import certifi

with open(certifi.where(), "rb") as f:
    certifi_ca = f.read()

with open("corp-root.pem", "rb") as f:
    corp_ca = f.read()

with open("combined.pem", "wb") as f:
    f.write(certifi_ca + b"\n" + corp_ca)

print("✅ combined.pem created")