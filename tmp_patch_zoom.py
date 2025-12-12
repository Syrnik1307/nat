import requests

url = "https://lectio.space"
admin_email = "S@gmail.com"
admin_password = "Testpass123"

token_resp = requests.post(f"{url}/api/jwt/token/", json={"email": admin_email, "password": admin_password}, verify=False)
print("token status", token_resp.status_code)
print(token_resp.text)
token_resp.raise_for_status()
access = token_resp.json().get("access")
assert access, "no access token"

payload = {
    "zoom_account_id": "6w5GrnCgSgaHwMFFbhmlKw",
    "zoom_client_id": "vNl9EzZTy6h2UifsGVERg",
    "zoom_client_secret": "jqMJb4R3UgOQ1Q2FEHtkv6Tkz3CxNX87",
    "zoom_user_id": "me",
}

patch_resp = requests.patch(
    f"{url}/accounts/api/admin/teachers/8/zoom/",
    json=payload,
    headers={"Authorization": f"Bearer {access}"},
    verify=False,
)
print("patch status", patch_resp.status_code)
print(patch_resp.text)
