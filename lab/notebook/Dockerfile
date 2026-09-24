FROM quay.io/jupyter/minimal-notebook:notebook-7.6.2
RUN pip install --no-cache-dir pandas matplotlib requests
COPY chertiot.py /tmp/chertiot.py
RUN SP=$(python -c "import site; print(site.getsitepackages()[0])") && cp /tmp/chertiot.py "$SP/chertiot.py" && python -c "import chertiot" 
COPY notebooks/ /home/jovyan/work/examples/
# chertIoTlab language pack: relabels the residual Jupyter-branded Help links (registered as the
# `en_GB` languagepack; overrides.json selects that locale — untranslated strings stay English).
# Installed as root so setuptools can build egg-info in the (root-owned) copied source tree.
COPY langpack /tmp/langpack
USER root
RUN pip install --no-cache-dir /tmp/langpack && rm -rf /tmp/langpack
USER jovyan
# CHERT-brand the JupyterLab browser-tab favicon (jupyter_server serves the lab page's favicons).
COPY chert-favicon.ico /usr/local/share/chert-favicon.ico
# Ship a settings override that disables the "official Jupyter news" prompt (Ask → Never).
COPY overrides.json /opt/conda/share/jupyter/lab/settings/overrides.json
# chertIoTlab rebrand: app name (About dialog/menu), custom logo CSS, and browser-tab title.
COPY branding/page_config.json /opt/conda/etc/jupyter/labconfig/page_config.json
COPY branding/jupyter_server_config.py /opt/conda/etc/jupyter/jupyter_server_config.py
# custom.css is served from the runtime config_dir/custom (~/.jupyter/custom for the jovyan user).
COPY branding/custom.css /home/jovyan/.jupyter/custom/custom.css
COPY branding/chert-logo.png /home/jovyan/.jupyter/custom/chert-logo.png
# Bake the language selection as a user setting (what the Settings ▸ Language switch writes) so the
# chertIoTlab (en_GB) catalog is active at bootstrap and the Help labels are relabelled.
COPY branding/translation.jupyterlab-settings /home/jovyan/.jupyter/lab/user-settings/@jupyterlab/translation-extension/plugin.jupyterlab-settings
USER root
RUN chown -R jovyan:users /home/jovyan/work /home/jovyan/.jupyter && \
    SP=$(python -c "import jupyter_server, os; print(os.path.dirname(jupyter_server.__file__))") && \
    install -m 0644 /usr/local/share/chert-favicon.ico "$SP/static/favicon.ico" && \
    for f in "$SP"/static/favicons/*.ico; do install -m 0644 /usr/local/share/chert-favicon.ico "$f"; done && \
    sed -i 's#<title>JupyterLab</title>#<title>chertIoTlab</title>#' /opt/conda/share/jupyter/lab/static/index.html
USER jovyan
