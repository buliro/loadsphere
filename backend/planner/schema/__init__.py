import graphene
from .queries import Query
from .mutations import Mutation
from .auth import AuthMutation, UserType, UserQuery

class Query(Query, UserQuery, graphene.ObjectType):
    pass

class Mutation(Mutation, AuthMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    types=[UserType]
)
