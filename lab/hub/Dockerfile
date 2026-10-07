FROM ghcr.io/chertsa/chertiot-base-jupyterhub:5.5.1
RUN pip install --no-cache-dir dockerspawner==14.0.0 oauthenticator==17.4.0 jupyterhub-idle-culler==1.4.0
COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
# CHERT branding for the Hub pages (spawn-progress, home, token): navbar logo + browser-tab favicon.
COPY chert-logo.png /srv/jupyterhub/chert-logo.png
COPY chert-favicon.ico /tmp/chert-favicon.ico
RUN F=$(find / -path '*/share/jupyterhub/static/favicon.ico' 2>/dev/null | head -1) && \
    test -n "$F" && install -m 0644 /tmp/chert-favicon.ico "$F" && rm /tmp/chert-favicon.ico
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
