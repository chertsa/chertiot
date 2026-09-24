FROM quay.io/jupyter/minimal-notebook:notebook-7.6.2
RUN pip install --no-cache-dir pandas matplotlib requests
COPY chertiot.py /tmp/chertiot.py
RUN SP=$(python -c "import site; print(site.getsitepackages()[0])") && cp /tmp/chertiot.py "$SP/chertiot.py" && python -c "import chertiot" 
COPY notebooks/ /home/jovyan/work/examples/
# CHERT-brand the JupyterLab browser-tab favicon (jupyter_server serves the lab page's favicons).
COPY chert-favicon.ico /usr/local/share/chert-favicon.ico
USER root
RUN chown -R jovyan:users /home/jovyan/work && \
    SP=$(python -c "import jupyter_server, os; print(os.path.dirname(jupyter_server.__file__))") && \
    install -m 0644 /usr/local/share/chert-favicon.ico "$SP/static/favicon.ico" && \
    for f in "$SP"/static/favicons/*.ico; do install -m 0644 /usr/local/share/chert-favicon.ico "$f"; done
USER jovyan
