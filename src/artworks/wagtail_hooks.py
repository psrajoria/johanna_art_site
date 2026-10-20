from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Collection


class CollectionViewSet(SnippetViewSet):
    model = Collection
    icon = "folder-open-inverse"
    menu_label = "Collections"
    menu_order = 190
    add_to_admin_menu = True
    list_display = ["name", "sort_order"]
    search_fields = ["name"]


register_snippet(CollectionViewSet)
