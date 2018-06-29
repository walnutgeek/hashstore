from typing import NamedTuple

from hashstore.bakery import Cake

def fn(n:Cake, i:int)->Cake :
    print(f'n:{n} i:{i}')
    return n

class Worker(NamedTuple):
    name: str
    id: int
    x: Cake

def fn2()->Worker:
    e = Worker("Guido", 5, Cake.new_portal())
    return e

