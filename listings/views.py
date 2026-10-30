from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Avg, Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from django.views.generic.edit import FormView

from .agent import answer_question
from .analytics import brand_summary_sql, detect_anomaly, yearly_price_trend
from .forms import AgentQuestionForm, ListingForm
from .models import Listing

SORT_OPTIONS = {
    "yeni": ("-created_at", "En yeni"),
    "ucuz": ("price", "Fiyat: düşükten yükseğe"),
    "pahali": ("-price", "Fiyat: yüksekten düşüğe"),
    "yil": ("-year", "Model yılı: yeniden eskiye"),
    "km": ("mileage_km", "Kilometre: azdan çoğa"),
}


class ListingListView(ListView):
    model = Listing
    template_name = "listings/listing_list.html"
    context_object_name = "listings"
    paginate_by = 12

    def get_queryset(self):
        qs = Listing.objects.all()
        g = self.request.GET

        brand = g.get("brand", "").strip()
        max_price = g.get("max_price", "").strip().replace(".", "")
        fuel = g.get("fuel", "").strip()
        sort = g.get("sort", "yeni")

        if brand:
            qs = qs.filter(brand__icontains=brand)
        if max_price.isdigit():
            qs = qs.filter(price__lte=int(max_price))
        if fuel:
            qs = qs.filter(fuel_type=fuel)

        order = SORT_OPTIONS.get(sort, SORT_OPTIONS["yeni"])[0]
        return qs.order_by(order, "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["query_string"] = params.urlencode()  # sayfa değişince filtreler kaybolmasın
        ctx["brands"] = Listing.objects.order_by("brand").values_list("brand", flat=True).distinct()
        ctx["fuel_choices"] = Listing.FUEL_CHOICES
        ctx["sort_options"] = [(k, v[1]) for k, v in SORT_OPTIONS.items()]
        ctx["current"] = {
            "brand": self.request.GET.get("brand", ""),
            "max_price": self.request.GET.get("max_price", ""),
            "fuel": self.request.GET.get("fuel", ""),
            "sort": self.request.GET.get("sort", "yeni"),
        }
        ctx["has_filters"] = any(ctx["current"][k] for k in ("brand", "max_price", "fuel"))
        ctx["total_count"] = Listing.objects.count()
        return ctx


class ListingDetailView(DetailView):
    model = Listing
    template_name = "listings/listing_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        analysis = detect_anomaly(self.object.pk)
        ctx["analysis"] = analysis

        # Fiyat cetveli: ortalama ortada, ±3 standart sapma kenarlarda
        if analysis.get("enough_data"):
            z = max(-3.0, min(3.0, analysis["z_score"]))
            ctx["meter_position"] = f"{(z + 3) / 6 * 100:.1f}"  # metin: Türkçe virgüle çevrilmesin

        ctx["similar"] = (
            Listing.objects.filter(
                brand=self.object.brand,
                model_name=self.object.model_name,
                year__gte=self.object.year - 2,
                year__lte=self.object.year + 2,
            )
            .exclude(pk=self.object.pk)
            .order_by("?")[:4]
        )
        return ctx


class ListingCreateView(SuccessMessageMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/listing_form.html"
    success_message = "İlan yayınlandı: %(brand)s %(model_name)s"

    def get_success_url(self):
        return reverse_lazy("listing-detail", args=[self.object.pk])


class ListingUpdateView(SuccessMessageMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/listing_form.html"
    success_message = "Değişiklikler kaydedildi."

    def get_success_url(self):
        return reverse_lazy("listing-detail", args=[self.object.pk])


class ListingDeleteView(SuccessMessageMixin, DeleteView):
    model = Listing
    template_name = "listings/listing_confirm_delete.html"
    success_url = reverse_lazy("listing-list")
    success_message = "İlan silindi."


class StatsView(TemplateView):
    template_name = "listings/stats.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        summary = brand_summary_sql()
        yearly = yearly_price_trend()
        totals = Listing.objects.aggregate(count=Count("id"), avg=Avg("price"))

        ctx["summary"] = summary
        ctx["totals"] = totals
        ctx["max_avg"] = max((r["avg_price"] for r in summary), default=0)
        ctx["chart_data"] = {
            "brands": {
                "labels": [r["brand"] for r in summary],
                "values": [r["avg_price"] for r in summary],
            },
            "years": {
                "labels": [r["year"] for r in yearly],
                "values": [r["avg_price"] for r in yearly],
            },
        }
        labels = dict(Listing.FUEL_CHOICES)
        total = totals["count"] or 1
        ctx["fuel_counts"] = [
            {"label": labels.get(r["fuel_type"], r["fuel_type"]), "n": r["n"],
             "pct": round(r["n"] * 100 / total)}
            for r in Listing.objects.values("fuel_type").annotate(n=Count("id")).order_by("-n")
        ]
        return ctx


class AgentChatView(FormView):
    """
    Sohbet geçmişi oturumda (session) tutulur. POST'tan sonra aynı sayfaya
    yönlendirilir (Post/Redirect/Get), böylece sayfa yenilenince soru tekrar gönderilmez.
    """
    template_name = "listings/agent_chat.html"
    form_class = AgentQuestionForm
    success_url = reverse_lazy("agent-chat")
    SESSION_KEY = "agent_history"
    MAX_HISTORY = 12

    EXAMPLES = [
        "2020 model BMW 3 Serisi kaç TL?",
        "Fiat Egea ortalama fiyatı ne kadar?",
        "Toyota Corolla alınır mı?",
        "5 numaralı ilanın fiyatı normal mi?",
    ]

    def post(self, request, *args, **kwargs):
        if "clear" in request.POST:
            request.session[self.SESSION_KEY] = []
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        question = form.cleaned_data["question"]
        result = answer_question(question)
        history = self.request.session.get(self.SESSION_KEY, [])
        history.append({"question": question, **result})
        self.request.session[self.SESSION_KEY] = history[-self.MAX_HISTORY:]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = self.request.session.get(self.SESSION_KEY, [])
        ctx["examples"] = self.EXAMPLES
        return ctx
