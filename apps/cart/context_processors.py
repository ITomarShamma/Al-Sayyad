"""يجعل «cart» متاحاً بكل قالب — الهيدر يعرض العدّاد بأي صفحة."""

from .cart import Cart


def cart(request):
    return {"cart": Cart(request)}
