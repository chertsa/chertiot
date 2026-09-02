FROM quay.io/jupyter/minimal-notebook:notebook-7.6.2
RUN pip install --no-cache-dir pandas matplotlib requests
COPY chertiot.py /opt/conda/lib/python3.12/site-packages/chertiot.py
COPY notebooks/ /home/jovyan/work/examples/
USER root
RUN chown -R jovyan:users /home/jovyan/work
USER jovyan
