from odoo import models, fields, exceptions, _

class HrLockMixin(models.AbstractModel):
    _name = 'hr.lock.mixin'
    _description = 'Mixin de Bloqueo de Registros RRHH'

    is_locked = fields.Boolean(
        string="Bloqueado por RRHH",
        default=False,
        copy=False,
        tracking=True,
        help="Si está marcado, solo los perfiles autorizados pueden editar."
    )

    def _check_lock_permission(self):
        """
        Método pensado para ser sobreescrito en cada módulo.
        Por defecto, solo el Administrador de Ajustes tiene permiso.
        """
        return self.env.user.has_group('base.group_system')

    def write(self, vals):
        # Permitimos siempre cambiar el estado y el candado (para que la lógica funcione)
        allowed_fields = {'state', 'is_locked', 'message_main_attachment_id'}

        for record in self:
            # Si ya está bloqueado y el usuario NO es RRHH/Admin
            if record.is_locked and not self._check_lock_permission():
                # Si intenta cambiar algo que NO está en la lista permitida
                if any(k for k in vals if k not in allowed_fields):
                    raise exceptions.UserError(_(
                        "🔒 REGISTRO BLOQUEADO\n"
                        "------------------------------------------\n\n"
                        "Lo sentimos, este registro ya no se puede modificar.\n\n"
                        "⚠️ Si necesitas realizar un cambio urgente, por favor contacta con el Encargado(a) de RRHH para que habilite la edición."
                    ))
        return super().write(vals)

    def unlink(self):
        """Evita la eliminación de registros bloqueados"""
        for record in self:
            if record.is_locked and not self._check_lock_permission():
                raise exceptions.UserError(_("No puedes eliminar un registro bloqueado."))
        return super().unlink()