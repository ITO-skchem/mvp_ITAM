from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def asset_ai_search(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return Response({"query": query, "results": []})

    try:
        from ai_search.services import AssetSearchService

        svc = AssetSearchService()
    except FileNotFoundError:
        return Response(
            {
                "query": query,
                "results": [],
                "message": "AI index not found. Run `python manage.py build_asset_index` first.",
            },
            status=503,
        )
    return Response({"query": query, "results": svc.search(query, k=5)})
