from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.forms.models import model_to_dict
from .models import Item
import json


def _item_to_dict(item: Item):
    d = model_to_dict(item)
    d["created_at"] = item.created_at.isoformat()
    return d

@require_http_methods(["GET"])
def items_list(request):
    items = Item.objects.order_by("-created_at").all()
    return JsonResponse({"items": [_item_to_dict(i) for i in items]})

@require_http_methods(["GET"])
def item_detail(request, item_id: int):
    try:
        item = Item.objects.get(pk=item_id)
        return JsonResponse({"item": _item_to_dict(item)})
    except Item.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def item_create(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        name = payload.get("name")
        description = payload.get("description", "")
        if not name:
            return JsonResponse({"error": "name_required"}, status=400)
        item = Item.objects.create(name=name, description=description)
        return JsonResponse({"item": _item_to_dict(item)}, status=201)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
