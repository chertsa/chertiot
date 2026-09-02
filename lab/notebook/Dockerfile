FROM quay.io/jupyter/minimal-notebook:notebook-7.6.2
RUN pip install --no-cache-dir pandas matplotlib requests
COPY chertiot.py /tmp/chertiot.py
RUN SP=$(python -c "import site; print(site.getsitepackages()[0])") && cp /tmp/chertiot.py "$SP/chertiot.py" && python -c "import chertiot" 
COPY notebooks/ /home/jovyan/work/examples/
USER root
RUN chown -R jovyan:users /home/jovyan/work
USER jovyan
