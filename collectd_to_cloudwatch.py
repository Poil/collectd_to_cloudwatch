import collectd
import boto.ec2.cloudwatch
from yaml import load as yload

REGION = False
AWS_ACCESS_KEY_ID = False
AWS_SECRET_ACCESS_KEY = False
NAMESPACE = False
METRICS = {}
cw_ec2 = False


def config(conf):
    collectd.debug('Configuring Stuff')
    global REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, NAMESPACE, METRICS

    if conf.region:
        REGION = conf.region
    if conf.aws_access_key_id:
        AWS_ACCESS_KEY_ID = conf.aws_access_key_id
    if conf.conf.aws_secret_access_key:
        AWS_SECRET_ACCESS_KEY = conf.aws_secret_access_key
    if conf.namespace:
        NAMESPACE = conf.namespace
    METRICS_CONFIG = conf.metrics_config
    collectd.debug('Loading YAML plugins configuration')
    try:
        METRICS = yload(METRICS_CONFIG)
    except:
        collectd.warn("Couldn't load YAML plugins configuration {0}").format(METRICS_CONFIG)


def init():
    collectd.debug('initing stuff')
    global cw_ec2, REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        try:
            cw_ec2 = boto.ec2.cloudwatch.connect_to_region(REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        except:
            collectd.warn("Couldn't connect to cloudwatch with your access_key")
    else:
        try:
            cw_ec2 = boto.ec2.cloudwatch.connect_to_region(REGION)
        except:
            collectd.warn("Couldn't connect to cloudwatch with your instance role")


def shutdown():
    collectd.debug('Shutting down collectd_to_cloudwatch plugin')


def write(vl, datas=None):
    global cw_ec2, NAMESPACE, METRICS

    # Get unit for current p/t/ti, if not exists, do nothing
    if METRICS.get(vl.plugin) and METRICS[vl.plugin].get(vl.type):

        if vl.plugin_instance:
            metric_name = '{p}{pi}{t}'.format(p=vl.plugin, pi=vl.plugin_instance.title(), t=vl.type.title())
        else:
            metric_name = '{p}{t}'.format(p=vl.plugin, t=vl.type.title())

        # Append type_instance to metric_name and get unit of the metric
        if vl.type_instance:
            metric_name = '{m}{ti}'.format(m=metric_name, ti=vl.type_instance.title())
            unit = METRICS[vl.plugin][vl.type][vl.type_instance]
        else:
            unit = METRICS[vl.plugin][vl.type]

        dimensions = 'Source=collectd, InstanceName={host} '.format(vl.host)
        # Needed ?
        if len(vl.values) > 1:
            for i in vl.values:
                collectd.debug('Putting {metric}={value}{unit} to {namespace} {dimensions}').format(metric=metric_name, value=i, unit=unit, namespace=NAMESPACE, dimensions=dimensions)
                cw_ec2.put_metric_data(namespace=NAMESPACE, name=metric_name, value=i, unit=unit, dimensions=dimensions)
        else:
            collectd.debug('Putting {metric}={value}{unit} to {namespace} {dimensions}').format(metric=metric_name, value=vl.values, unit=unit, namespace=NAMESPACE, dimensions=dimensions)
            cw_ec2.put_metric_data(namespace=NAMESPACE, name=metric_name, value=vl.values, unit=unit, dimensions=dimensions)


collectd.register_config(config)
collectd.register_init(init)
collectd.register_shutdown(shutdown)
collectd.register_write(write)
