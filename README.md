### MVP - PMC
Un bot de Whatsapp para la consulta de cupos de parqueaderos en tiempo real, utilizando LLMs y herramientas personalizadas.

### Docker
Existen dos versiones de docker-compose:
- `dev.docker-compose.yml`: Para desarrollo local, con recarga constante, no se debe usar en producción.
- `prod.docker-compose.yml`: Para producción, sin recarga, optimizado para despliegue.
Hacer el compose: 
#### Local (desarrollo)
```bash
docker-compose -f dev.docker-compose.yml up --build
```

#### Producción
```bash
docker-compose -f prod.docker-compose.yml up --build -d
```