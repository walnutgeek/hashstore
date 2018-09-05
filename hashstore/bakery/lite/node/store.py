from hashstore.bakery import (HashSession, CakePath, LookupInfo,
                              PathInfo, PathResolved)


class LiteSession(HashSession):
    def __init__(self,user):
        """

        """
        ...

    def _resolve(self, path: CakePath) -> PathResolved:
        ...

    def get_info(self, cake_path: CakePath )->PathInfo:
        ...

    def get_content(self, cake_path: CakePath ) -> LookupInfo:
        ...
