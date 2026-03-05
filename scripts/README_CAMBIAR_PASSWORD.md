# Cambiar contraseña del usuario admin

## Opción 1: Generar hash y actualizar la BD en Render a mano

1. En la carpeta del proyecto (donde está `app.py`), ejecute:
   ```bash
   python scripts/generar_hash_password.py
   ```
   Escriba la nueva contraseña cuando se le pida (o pásela como argumento):
   ```bash
   python scripts/generar_hash_password.py "MiNuevaContraseña"
   ```

2. El script mostrará un **hash** y una línea **SQL**. Copie solo el hash (la línea larga que empieza con `$2b$12$...`).

3. En **Render**:
   - Entra a tu servicio **PostgreSQL**.
   - Pestaña **"Connect"** o **"Shell"** (o usa **psql** con la External Database URL).
   - Ejecuta este SQL (reemplace `EL_HASH_QUE_COPIO` por el hash generado):
   ```sql
   UPDATE seguridad.usuarios SET password_hash = 'EL_HASH_QUE_COPIO' WHERE username = 'admin';
   ```

4. Ya puede iniciar sesión con usuario **admin** y la **nueva contraseña**.

---

## Opción 2: Actualizar la BD en línea desde su PC con un script

Si tiene la **URL de la base de datos de Render** (External Database URL), puede actualizar sin entrar a Render:

1. En la carpeta del proyecto, ejecute (sustituya `SuNuevaContraseña` y la URL):
   ```bash
   set DATABASE_URL=postgres://usuario:contraseña@host.render.com:5432/nombre_bd
   python scripts/actualizar_password_admin.py "SuNuevaContraseña"
   ```
   En PowerShell:
   ```powershell
   $env:DATABASE_URL="postgres://usuario:contraseña@host.render.com:5432/nombre_bd"
   python scripts/actualizar_password_admin.py "SuNuevaContraseña"
   ```

2. El script se conecta a la BD en línea y actualiza el `password_hash` del usuario **admin**.

**Nota:** No deje la URL guardada en el historial de la consola si comparte el equipo. Puede usar un archivo `.env` solo en su PC con `DATABASE_URL=...` y ejecutar:
```bash
python scripts/actualizar_password_admin.py "SuNuevaContraseña"
```
