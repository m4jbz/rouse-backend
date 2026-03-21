# Estructura de las carpetas y archivos del proyecto

En la carpeta raiz o root existen las siguientes carpetas y archivos:

* **.env**: Archivo para variables de entorno, es una medida de seguridad para no
colocar credenciales directamente en el código.
* **.gitignore**: Archivo para colocar los archivos y carpetas que no se quieran subir al
repositorio.
* **.venv/**: Carpeta con todos los archivos necesarios para el entorno virtual de python.
* **README.md**: Archivo para mostrarlo en el repositorio de GitHub con la información
más útil del proyecto, como construirlo y correrlo.
* **docker-compose.yaml**: Archivo docker compose para poder crear la BD y su cliente
adminer.
* **requirements.txt**: Archivo con las librerías y paquetes de python usados en
el proyecto.
* **railway.toml**: Archivo necesario para railway (plataforma host del backend) para
actualizar la conexión con la BD cada que se reinicie el backend.
* **alembic.ini**: Archivo generado automaticamente para alembic (librería de ayuda para
la BD), con sus configuraciones necesarias.
* **Procfile**: Archivo para railway para poder subir y desplegar sin errores el proyecto.
* **alembic/**:  Carpeta con archivos necesarios para migraciones de la BD, así como las
versiones de las queries hechas en la BD.
* **app/**: Carpeta principal del proyecto, aquí se encuentra todo el código que conforma el backend.
* **docs/**: Carpeta de archivos de documentación.
