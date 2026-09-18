from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Listing
from .forms import ListingForm
from django.views.generic.edit import FormView
from .forms import AgentQuestionForm
from .agent import ask_agent

class ListingListView(ListView):
    model = Listing
    template_name = "listings/listing_list.html"
    context_object_name = "listings"
    paginate_by = 12
    ordering = ["-created_at"]

class ListingDetailView(DetailView):
    model = Listing
    template_name = "listings/listing_detail.html"

class ListingCreateView(CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/listing_form.html"
    success_url = reverse_lazy("listing-list")

class ListingUpdateView(UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/listing_form.html"
    success_url = reverse_lazy("listing-list")

class ListingDeleteView(DeleteView):
    model = Listing
    template_name = "listings/listing_confirm_delete.html"
    success_url = reverse_lazy("listing-list")
class AgentChatView(FormView):
    template_name = "listings/agent_chat.html"
    form_class = AgentQuestionForm

    def form_valid(self, form):
        question = form.cleaned_data["question"]
        answer = ask_agent(question)
        context = self.get_context_data(form=form)
        context["question"] = question
        context["answer"] = answer
        return self.render_to_response(context)