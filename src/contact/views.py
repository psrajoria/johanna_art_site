from django.shortcuts import redirect, render

from artworks.models import ArtworkPage

from .forms import InquiryForm
from .models import Inquiry


def inquiry_create(request):
    artwork = None

    artwork_id = request.GET.get("artwork") or request.POST.get("artwork_id")
    if artwork_id:
        artwork = ArtworkPage.objects.live().public().filter(id=artwork_id).first()

    initial = {}

    if artwork:
        initial["inquiry_type"] = Inquiry.INQUIRY_ARTWORK
    elif request.GET.get("type") == "commission":
        initial["inquiry_type"] = Inquiry.INQUIRY_COMMISSION

    if request.method == "POST":
        form = InquiryForm(request.POST)

        if form.is_valid():
            inquiry = form.save(commit=False)

            if artwork:
                inquiry.artwork = artwork

            inquiry.save()

            return redirect("contact:thanks")
    else:
        form = InquiryForm(initial=initial)

    return render(
        request,
        "contact/inquiry_form.html",
        {
            "form": form,
            "artwork": artwork,
        },
    )


def thanks(request):
    return render(request, "contact/thanks.html")
