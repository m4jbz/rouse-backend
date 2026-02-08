# Backend de la pasteleria Rouse

## Base de datos y adminer con docker compose

Usamos postgresql como sistema gestor de base de datos y adminer como cliente web de postgresql.
Ambos estan juntos en un contenedor de docker el cual se puede usar con el siguiente comando:

```bash
docker compose up -d
```

Las credenciales estan dentro del archivo [docker-compose.yaml](docker-compose.yaml).

## Instalar dependencias

Primero se recomienda crear un virual enviroment de python con el comando:

```bash
python -m venv .venv
```

para activarlo con:

```bash
source .venv/bin/activate
```

para desactivarlo con:

```bash
deactivate
```

Las librerias/dependencias de este proyecto estan en el archivo [requirements.txt](requirements.txt),
se instalan con el comando:

```bash
pip install -r requirements.txt
```

## Correr el programa

```bash
fastapi dev app/main.py
```

El backend corre en el puerto 8000