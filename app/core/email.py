import logging

import resend

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, name: str, token: str) -> bool:
    # Envía un correo de verificación al cliente.
    # Devuelve True si el correo se envió correctamente, False en caso contrario.
    verification_url = f"{settings.FRONTEND_HOST}/verify-email?token={token}"

    try:
        resend.Emails.send(
            {
                "from": settings.VERIFY_EMAIL,
                "to": [to_email],
                "subject": "Verifica tu cuenta - Pastelería Rouse",
                "html": f"""
                <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #C8923A; font-family: 'Playfair Display', Georgia, serif; font-size: 28px; margin: 0;">
                            Pastelería Rouse
                        </h1>
                    </div>
                    <div style="background: #FAF4EB; border: 1px solid #D4B888; border-radius: 12px; padding: 32px;">
                        <h2 style="color: #3E2412; margin-top: 0;">¡Hola, {name}!</h2>
                        <p style="color: #6B4422; line-height: 1.6;">
                            Gracias por registrarte en Pastelería Rouse. Para completar tu registro,
                            haz clic en el siguiente botón para verificar tu correo electrónico:
                        </p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{verification_url}"
                               style="background: #C8923A; color: white; padding: 14px 32px; text-decoration: none;
                                      border-radius: 6px; font-weight: 600; display: inline-block;">
                                Verificar mi cuenta
                            </a>
                        </div>
                        <p style="color: #6B4422; font-size: 14px; line-height: 1.5;">
                            Este enlace expira en {settings.EMAIL_TOKEN_EXPIRE_MINUTES} minutos.
                            Si no creaste esta cuenta, puedes ignorar este correo.
                        </p>
                        <hr style="border: none; border-top: 1px solid #D4B888; margin: 24px 0;" />
                        <p style="color: #6B4422; font-size: 12px; margin: 0;">
                            Si el botón no funciona, copia y pega este enlace en tu navegador:<br />
                            <a href="{verification_url}" style="color: #C8923A; word-break: break-all;">
                                {verification_url}
                            </a>
                        </p>
                    </div>
                </div>
                """,
            }
        )
        return True
    except Exception as e:
        logger.error("Hubo un error al enviar el correo de verificación a %s: %s", to_email, e)
        return False


def send_password_reset_email(to_email: str, name: str, token: str) -> bool:
    # Envía un correo de restablecimiento de contraseña al cliente.
    # Devuelve True si el correo se envió correctamente, False en caso contrario.
    reset_url = f"{settings.FRONTEND_HOST}/reset-password?token={token}"

    try:
        resend.Emails.send(
            {
                "from": settings.RESET_PASSWORD_EMAIL,
                "to": [to_email],
                "subject": "Restablecer contraseña - Pastelería Rouse",
                "html": f"""
                <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #C8923A; font-family: 'Playfair Display', Georgia, serif; font-size: 28px; margin: 0;">
                            Pastelería Rouse
                        </h1>
                    </div>
                    <div style="background: #FAF4EB; border: 1px solid #D4B888; border-radius: 12px; padding: 32px;">
                        <h2 style="color: #3E2412; margin-top: 0;">Restablecer contraseña</h2>
                        <p style="color: #6B4422; line-height: 1.6;">
                            Hola {name}, recibimos una solicitud para restablecer la contraseña de tu cuenta.
                            Haz clic en el siguiente botón para crear una nueva contraseña:
                        </p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_url}"
                               style="background: #C8923A; color: white; padding: 14px 32px; text-decoration: none;
                                      border-radius: 6px; font-weight: 600; display: inline-block;">
                                Restablecer contraseña
                            </a>
                        </div>
                        <p style="color: #6B4422; font-size: 14px; line-height: 1.5;">
                            Este enlace expira en {settings.RESET_TOKEN_EXPIRE_MINUTES} minutos.
                            Si no solicitaste este cambio, puedes ignorar este correo.
                        </p>
                        <hr style="border: none; border-top: 1px solid #D4B888; margin: 24px 0;" />
                        <p style="color: #6B4422; font-size: 12px; margin: 0;">
                            Si el botón no funciona, copia y pega este enlace en tu navegador:<br />
                            <a href="{reset_url}" style="color: #C8923A; word-break: break-all;">
                                {reset_url}
                            </a>
                        </p>
                    </div>
                </div>
                """,
            }
        )
        return True
    except Exception as e:
        logger.error("Hubo un error al enviar el correo de restablecimiento de contraseña a %s: %s", to_email, e)
        return False
