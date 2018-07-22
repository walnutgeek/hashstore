from typing import NamedTuple

from hashstore.bakery import Cake
from hashstore.bakery.logic import Task, Dag, DagVariable


def fn(n:Cake, i:int)->Cake :
    print(f'n:{n} i:{i}')
    return n


class Worker(NamedTuple):
    name: str
    id: int
    x: Cake


def fn2()->Worker:
    e = Worker("Guido", 5, Cake.new_portal())
    print(e)
    return e


def fn3(n:Cake, i:int = 5)->Cake :
    print(f'fn3 n:{n} i:{i}')
    return n

class DagFn(Dag):
    z = DagVariable(int)
    task1 = Task(fn2)
    task2 = Task(fn, n=task1.output.x, i=z)


