# -*- coding: utf-8 -*-
"""
Modulo 2 - Listas de datos del analisis estatico de URL  ·  Alex

Todo lo que es "conocimiento del dominio" (marcas, TLD, acortadores,
homoglifos) vive aqui para poder ampliarlo sin tocar la logica.
"""
from __future__ import annotations

# ---------------------------------------------------------------- TLD
# Clasificacion por riesgo. Criterio: registro barato o gratuito, poca
# verificacion de identidad y ratio historico alto de abuso (Spamhaus,
# Interisle "Phishing Landscape"). .zip y .mov son especialmente malos
# porque el nombre coincide con extensiones de fichero.
TLD_ALTO = {
    "zip", "mov", "top", "xyz", "click", "link", "tk", "ml", "ga", "cf",
    "gq", "buzz", "rest", "country", "kim", "work", "cfd", "sbs", "cyou",
    "bond", "quest", "monster", "lol", "icu", "surf", "autos", "beauty",
    "hair", "skin", "makeup", "mom", "pics", "men", "loan", "download",
    "stream", "racing", "win", "review", "date", "party", "accountant",
    "science", "gdn", "wang", "fit", "casa", "uno", "pw", "su",
}
TLD_MEDIO = {
    "info", "biz", "online", "site", "shop", "store", "space", "website",
    "club", "fun", "life", "today", "digital", "live", "cc", "us", "ws",
    "vip", "world", "email", "support", "services", "center", "cloud",
    "host", "press", "agency", "solutions", "one", "now", "asia",
}

# Extensiones de fichero que, apareciendo en la ruta, son descarga directa.
EXTENSIONES_PELIGROSAS = (
    ".apk", ".exe", ".msi", ".scr", ".bat", ".cmd", ".vbs", ".js", ".jar",
    ".lnk", ".iso", ".img", ".dmg", ".pkg", ".ps1", ".hta", ".zip", ".rar",
    ".7z",
)
# .html y .htm quedan fuera a proposito: media web legitima termina asi.

# ---------------------------------------------------------------- Marcas
# marca -> dominios legitimos. Si el dominio registrable coincide con
# alguno de estos NO es typosquat (evita falsos positivos con la web real).
MARCAS: dict[str, tuple[str, ...]] = {
    # Paqueteria y logistica (el senuelo numero 1 del quishing)
    "correos":         ("correos.es", "correos.com"),
    "correosexpress":  ("correosexpress.com",),
    "seur":            ("seur.com", "seur.es"),
    "mrw":             ("mrw.es",),
    "gls":             ("gls-spain.es", "gls-group.eu"),
    "dhl":             ("dhl.com", "dhl.es"),
    "ups":             ("ups.com",),
    "fedex":           ("fedex.com",),
    "tipsa":           ("tip-sa.com",),
    "inpost":          ("inpost.es",),
    # Administracion publica
    "dgt":             ("dgt.es",),
    "aeat":            ("agenciatributaria.es", "agenciatributaria.gob.es", "aeat.es"),
    "agenciatributaria": ("agenciatributaria.es", "agenciatributaria.gob.es"),
    "seguridadsocial": ("seg-social.es", "seg-social.gob.es"),
    "segsocial":       ("seg-social.es", "seg-social.gob.es"),
    "sepe":            ("sepe.es", "sepe.gob.es"),
    "policia":         ("policia.es",),
    # Banca
    "bbva":            ("bbva.es", "bbva.com"),
    "santander":       ("bancosantander.es", "santander.com", "santander.es"),
    "caixabank":       ("caixabank.es", "caixabank.com"),
    "lacaixa":         ("lacaixa.es",),
    "sabadell":        ("bancsabadell.com", "sabadell.com"),
    "bankinter":       ("bankinter.com",),
    "unicaja":         ("unicajabanco.es",),
    "ibercaja":        ("ibercaja.es",),
    "kutxabank":       ("kutxabank.es",),
    "openbank":        ("openbank.es",),
    "abanca":          ("abanca.com",),
    "cajamar":         ("cajamar.es",),
    "evobanco":        ("evobanco.com",),
    "bizum":           ("bizum.es",),
    "paypal":          ("paypal.com", "paypal.es"),
    "revolut":         ("revolut.com",),
    # Suministros y telecos
    "endesa":          ("endesa.com", "endesaclientes.com"),
    "iberdrola":       ("iberdrola.es", "iberdrola.com"),
    "naturgy":         ("naturgy.es", "naturgy.com"),
    "repsol":          ("repsol.es", "repsol.com"),
    "movistar":        ("movistar.es", "telefonica.com"),
    "vodafone":        ("vodafone.es", "vodafone.com"),
    "orange":          ("orange.es",),
    "yoigo":           ("yoigo.com",),
    "masmovil":        ("masmovil.es",),
    # Tecnologicas y servicios
    "microsoft":       ("microsoft.com",),
    "office365":       ("office.com", "office365.com"),
    "outlook":         ("outlook.com", "live.com"),
    "google":          ("google.com", "google.es"),
    "gmail":           ("gmail.com",),
    "apple":           ("apple.com",),
    "icloud":          ("icloud.com",),
    "amazon":          ("amazon.es", "amazon.com"),
    "netflix":         ("netflix.com",),
    "whatsapp":        ("whatsapp.com",),
    "instagram":       ("instagram.com",),
    "facebook":        ("facebook.com", "fb.com"),
    "linkedin":        ("linkedin.com",),
    "dropbox":         ("dropbox.com",),
    "steam":           ("steampowered.com", "steamcommunity.com"),
    # Comercio y transporte
    "elcorteingles":   ("elcorteingles.es",),
    "mercadona":       ("mercadona.es",),
    "wallapop":        ("wallapop.com",),
    "vinted":          ("vinted.es", "vinted.com"),
    "milanuncios":     ("milanuncios.com",),
    "renfe":           ("renfe.com", "renfe.es"),
    "iberia":          ("iberia.com",),
    "glovo":           ("glovoapp.com",),
    # Cripto (quishing de "airdrop" y de cajeros de bitcoin)
    "binance":         ("binance.com",),
    "coinbase":        ("coinbase.com",),
    "metamask":        ("metamask.io",),
    "ledger":          ("ledger.com",),
}

# Marcas cortas: exigen coincidencia exacta del label o separador claro.
# Si no, "dgt" o "ups" saltarian dentro de cualquier palabra.
MARCAS_CORTAS = {m for m in MARCAS if len(m) <= 4}

# Dominios de infraestructura o de segunda marca que llevan el nombre de
# una marca dentro y son legitimos. Sin esta lista, amazonaws.com o
# microsoftonline.com se marcarian como typosquat de amazon y microsoft.
DOMINIOS_LEGITIMOS: set[str] = {d for dominios in MARCAS.values() for d in dominios} | {
    "amazonaws.com", "awsstatic.com", "media-amazon.com", "ssl-images-amazon.com",
    "googleapis.com", "googleusercontent.com", "gstatic.com", "goo.gle",
    "microsoftonline.com", "office.net", "sharepoint.com", "onedrive.com",
    "azureedge.net", "windows.net", "msn.com", "bing.com", "skype.com",
    "apple.news", "cdn-apple.com", "icloud-content.com", "mzstatic.com",
    "paypalobjects.com", "netflix.net", "nflximg.net", "fbcdn.net",
    "cdninstagram.com", "whatsapp.net", "licdn.com", "twimg.com",
    "correos.post", "seg-social.es", "administracion.gob.es", "060.es",
    "santanderconsumer.es", "bbvaapimarket.com", "caixabankbenefits.com",
}

# ---------------------------------------------------------------- Acortadores
ACORTADORES = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy", "v.gd",
    "shorturl.at", "ow.ly", "acortar.link", "buff.ly", "t.ly", "s.id",
    "goo.gl", "rebrand.ly", "bit.do", "tiny.cc", "lnkd.in", "qrco.de",
    "shrtco.de", "u.to", "chilp.it", "clck.ru", "vk.cc", "surl.li",
    "short.gy", "tr.ee", "linktr.ee", "gg.gg", "kutt.it", "urlz.fr",
}

# ---------------------------------------------------------------- Deep links
# Esquemas que no son web: abren una app del movil. En un QR son senal
# fuerte porque el usuario no ve nunca el destino antes de escanear.
ESQUEMAS_APP = {
    "telegram": "Telegram", "tg": "Telegram", "whatsapp": "WhatsApp",
    "intent": "Android intent (puede abrir cualquier app)",
    "android-app": "Android", "market": "Google Play",
    "itms-apps": "App Store",
    "itms-services": "instalacion de app fuera de la App Store",
    "fb": "Facebook", "instagram": "Instagram", "twitter": "X/Twitter",
    "viber": "Viber", "sgnl": "Signal", "skype": "Skype", "zoommtg": "Zoom",
    "bitcoin": "pago en Bitcoin", "ethereum": "pago en Ethereum",
    "upi": "pago UPI", "tel": "llamada telefonica", "sms": "envio de SMS",
    "smsto": "envio de SMS", "mailto": "envio de correo",
    "javascript": "ejecucion de codigo", "data": "contenido embebido",
    "file": "fichero local", "ftp": "FTP", "wifi": "configuracion de wifi",
}

# ---------------------------------------------------------------- Homoglifos
# Caracteres que "se leen" como una letra latina. Se usan para calcular el
# esqueleto del dominio antes de compararlo con las marcas.
HOMOGLIFOS = {
    # digitos y simbolos
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "6": "b", "7": "t",
    "8": "b", "9": "g", "$": "s", "@": "a", "|": "l", "!": "i",
    # cirilico
    "а": "a", "в": "b", "с": "c", "е": "e", "н": "h",
    "к": "k", "м": "m", "о": "o", "р": "p", "ѕ": "s",
    "т": "t", "у": "y", "х": "x", "і": "i", "ј": "j",
    "ԁ": "d", "ɡ": "g", "ц": "u", "ԝ": "w", "ғ": "f",
    # griego
    "α": "a", "β": "b", "ε": "e", "ζ": "z", "η": "n",
    "ι": "i", "κ": "k", "ο": "o", "ρ": "p", "τ": "t",
    "υ": "u", "χ": "x", "γ": "y", "σ": "o", "ν": "v",
    # otros
    "ł": "l", "ø": "o", "đ": "d", "ı": "i", "ǀ": "l",
}

# Pares de letras que juntas imitan a otra letra.
BIGRAMAS_HOMOGLIFOS = (("rn", "m"), ("vv", "w"), ("cl", "d"), ("nn", "m"))

# ---------------------------------------------------------------- Lexico
# Palabras tipicas del gancho. No condenan por si solas, pero suman.
PALABRAS_GANCHO = {
    "login", "signin", "acceso", "acceder", "verificar", "verificacion",
    "validar", "confirmar", "confirmacion", "actualizar", "actualizacion",
    "seguridad", "seguro", "cuenta", "clave", "password", "contrasena",
    "credenciales", "otp", "sms", "2fa", "token", "firma", "certificado",
    "pago", "pagar", "abonar", "tasa", "tasas", "aduana", "aduanas",
    "envio", "paquete", "entrega", "reparto", "recogida", "seguimiento",
    "tracking", "factura", "recibo", "multa", "sancion", "reembolso",
    "devolucion", "premio", "sorteo", "regalo", "urgente", "bloqueada",
    "suspendida", "caducada", "pendiente", "reactivar", "desbloquear",
    "bizum", "iban", "tarjeta", "dni", "nie", "identidad",
}

# Parametros usados en redirecciones abiertas.
PARAMS_REDIRECCION = {
    "url", "redirect", "redirect_uri", "redir", "next", "target", "dest",
    "destination", "continue", "return", "returnurl", "goto", "out", "u", "r",
    "q", "link", "to", "src", "jump", "page", "view", "window",
}

# User-Agent neutro para expandir acortadores. Movil, porque muchas
# campanas de quishing solo redirigen si creen que hay un movil detras.
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)
