from mo import Properties, translate

properties = Properties()

properties.add_text("client_id", label=translate("emotiv.client_id"))
properties.set_default("client_id", "")

properties.add_text("client_secret", label=translate("emotiv.client_secret"))
properties.set_default("client_secret", "")
