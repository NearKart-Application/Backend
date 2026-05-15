# Screenshots Guide

Take these screenshots as you follow HOW_TO_RUN_AND_TEST.md and save them here.

## Screenshots to capture:

| Filename | What to screenshot |
|----------|--------------------|
| `01_venv_activated.png` | Terminal showing `(venv)` prompt after `source venv/bin/activate` |
| `02_pip_install_done.png` | Terminal showing successful `pip install -r requirements/development.txt` |
| `03_docker_running.png` | Docker Desktop showing all 6 containers green |
| `04_swagger_ui.png` | Browser at http://localhost:8000/api/docs/ showing NearKart API |
| `05_postman_env_setup.png` | Postman Environments panel with NearKart Local variables |
| `06_postman_otp_send.png` | Postman POST /otp/send/ → 200 response |
| `07_postman_otp_verify.png` | Postman POST /otp/verify/ → tokens in response |
| `08_postman_me.png` | Postman GET /me/ with Bearer token → user data |
| `09_postman_401.png` | Postman GET /me/ without token → 401 error |
| `10_django_admin.png` | Browser http://localhost:8000/admin/ showing Users list |

## How to take a Mac screenshot:
- Selected area: `Cmd + Shift + 4` then drag over the area
- Window only: `Cmd + Shift + 4` then press `Space` and click the window
- Full screen: `Cmd + Shift + 3`

Screenshots save to your Desktop by default.
Drag them into this `docs/images/` folder and rename to match the table above.
