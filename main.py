import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
import requests
from fastapi.background import BackgroundTasks

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)

redis = get_redis_connection(
    host='redis-19554.c289.us-west-1-2.ec2.cloud.redislabs.com',
    port=19554,
    password='crm5PXMqPiKEGP38oH1YAxK12Qh4If7V',
    decode_responses=True
)

class ProductOrder(HashModel):
    product_id: str
    quantity: int

    class Meta:
        database = redis

class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int
    status: str

    class Meta:
        database = redis

def format(pk: str):
    order = Order.get(pk)
    return {
        'id': order.pk,
        'product_id': order.product_id,
        'fee': order.fee,
        'price': order.prrice,
        'total': order.total,
        'status': order.status
    }


@app.post('/orders')
def create(productOrder: ProductOrder, background_tasks: BackgroundTasks):
    req = requests.get(f'http://localhost:8000/product/{productOrder.product_id}')
    product = req.json()

    fee = product['price'] * 0.2

    order = Order(
        product_id = productOrder.product_id,
        price = product['price'],
        fee =fee,
        total = product['price'] + fee,
        quantity=productOrder.quantity,
        status = 'pending'
    )

    order.save()

    # order_complete(order)
    background_tasks.add_task(order_complete, order)

    return order

@app.get('/orders/{pk}')
async def get(pk:str):
    return format(pk)

@app.get('/orders')
async def get_all():
    return [format(pk) for pk in Order.all_pks()]

def order_complete(order: Order):
    time.sleep(5)
    order.status = 'completed'
    order.save()
    redis.xadd(name='order-completed', fields=order.dict())
    