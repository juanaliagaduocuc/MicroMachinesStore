# MicroMachinesStore
Servicio de Ventas de Vehiculo en Miniatura Personalizables

## Despliegue en Render

El archivo `render.yaml` configura el servicio web y PostgreSQL. En Render, crea un Blueprint desde este repositorio y confirma los recursos propuestos. El proceso instala `app/requirements.txt`, recopila archivos estáticos y aplica migraciones antes de iniciar Django con Gunicorn.

Render genera `SECRET_KEY` y conecta la base PostgreSQL automáticamente. `DEBUG` queda desactivado. Después del primer despliegue, crea un administrador en la Shell del servicio con `python manage.py createsuperuser`; luego podrás cargar productos desde `/admin/`. No ejecutes `seed_store_data` en producción: crea cuentas de prueba con contraseñas fijas.

El plan gratuito de PostgreSQL de Render tiene límites y puede caducar; para conservar datos de producción usa un plan con persistencia adecuada y copias de seguridad.
