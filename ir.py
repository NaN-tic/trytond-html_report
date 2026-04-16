# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta


class ModelAccess(metaclass=PoolMeta):
    __name__ = 'ir.model.access'

    @classmethod
    def get_access(cls, models):
        pool = Pool()
        known_models = []
        missing_models = []
        for model in models:
            try:
                pool.get(model)
            except KeyError:
                missing_models.append(model)
            else:
                known_models.append(model)

        access = super().get_access(known_models)
        if missing_models:
            default = {'read': False, 'write': False,
                'create': False, 'delete': False}
            for model in missing_models:
                access[model] = default.copy()
        return access
