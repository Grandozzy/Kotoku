from django.http import Http404
from rest_framework.views import APIView

from apps.templates.api.serializers import ScenarioTemplateSerializer
from apps.templates.selectors import TemplateSelector
from common.exceptions import DomainError
from common.pagination import DefaultPagination
from common.responses import ok


class TemplateListView(APIView):
    def get(self, request):
        qs = TemplateSelector.list_templates()
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ScenarioTemplateSerializer(page, many=True)
        return ok({
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        })


class TemplateDetailView(APIView):
    def get(self, request, slug: str):
        try:
            template = TemplateSelector.get_by_slug(slug)
        except DomainError:
            raise Http404 from None
        return ok({"template": ScenarioTemplateSerializer(template).data})
