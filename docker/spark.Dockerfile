FROM bitnami/spark:3.5

USER root

# Python dependencies for PySpark UDFs
RUN pip install --no-cache-dir \
        rasterio==1.3.* \
        pyproj>=3.6 \
        shapely>=2.0

# Copy Spark jobs and config
COPY spark/jobs  /opt/spark/jobs
COPY spark/conf/spark_defaults.conf /opt/bitnami/spark/conf/spark-defaults.conf

RUN mkdir -p /opt/spark/logs && chmod 777 /opt/spark/logs

USER 1001
