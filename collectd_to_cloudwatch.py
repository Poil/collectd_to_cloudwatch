import collectd
import boto.ec2.cloudwatch
import boto.utils
from yaml import load as yload

REGION = False
AWS_ACCESS_KEY_ID = False
AWS_SECRET_ACCESS_KEY = False
NAMESPACE = "COLLECTD"
METRICS = {}
cw_ec2 = None
INSTANCE_ID = False


def config(conf):
    collectd.debug('Configuring Stuff')
    global REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, NAMESPACE, METRICS, INSTANCE_ID

    for node in conf.children:
        if node.key == 'region':
            REGION = node.values[0]
        if node.key == 'aws_access_key_id':
            AWS_ACCESS_KEY_ID = node.values[0]
        if node.key == 'aws_secret_access_key':
            AWS_SECRET_ACCESS_KEY = node.values[0]
        if node.key == 'namespace':
            NAMESPACE = node.values[0]
        if node.key == 'metrics_config':
            metrics_config = node.values[0]

    if not metrics_config:
        collectd.warning("Missing YAML plugins configuration please define metrics_config")
    
    collectd.debug('Loading YAML plugins configuration')
    try:
        stream = open(metrics_config)
        METRICS = yload(stream)
    except:
        collectd.warning(("Couldn't load YAML plugins configuration {0}").format(metrics_config))

    # get instance ID
    INSTANCE_ID = boto.utils.get_instance_metadata()['instance-id']


def init():
    collectd.debug('initing stuff')
    global cw_ec2, REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        try:
            cw_ec2 = boto.ec2.cloudwatch.connect_to_region(REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        except:
            collectd.warning("Couldn't connect to cloudwatch with your access_key")
    else:
        try:
            cw_ec2 = boto.ec2.cloudwatch.connect_to_region(REGION)
        except:
            collectd.warning("Couldn't connect to cloudwatch with your instance role")


def shutdown():
    collectd.debug('Shutting down collectd_to_cloudwatch plugin')


def write(vl, datas=None):
    global cw_ec2, NAMESPACE, METRICS, INSTANCE_ID

    # Get config for current p/t, if not exists, do nothing
    if METRICS.get(vl.plugin) and METRICS[vl.plugin].get(vl.type):
        # Get default plugin unit
        unit = METRICS[vl.plugin][vl.type].get('unit', 'None')

        # Build Metric Name (like FS because I can't have a beautifull CamelCase with collectd's name)
        if vl.plugin_instance:
            metric_name = '{p}-{pi}/{t}'.format(p=vl.plugin, pi=vl.plugin_instance, t=vl.type)
        else:
            metric_name = '{p}/{t}'.format(p=vl.plugin, t=vl.type)

        # Append type_instance to metric_name and get the unit of the metric if exists
        if vl.type_instance:
            metric_name = '{m}-{ti}'.format(m=metric_name, ti=vl.type_instance)
            if METRICS[vl.plugin][vl.type].get('type_instance', False):
                unit = METRICS[vl.plugin][vl.type]['type_instance'].get(vl.type_instance, unit)

        dimensions = {'InstanceId': INSTANCE_ID}
        # Needed ?
        for i in vl.values:
            collectd.debug(('Putting {metric}={value} {unit} to {namespace} {dimensions}').format(metric=metric_name, value=i, unit=unit, namespace=NAMESPACE, dimensions=dimensions))
            try:
                cw_ec2.put_metric_data(namespace=NAMESPACE, name=metric_name, value=float(i), unit=unit, dimensions=dimensions)
            except:
                collectd.debug(('Fail to put {metric}={value} {unit} to {namespace} {dimensions}').format(metric=metric_name, value=i, unit=unit, namespace=NAMESPACE, dimensions=dimensions))


collectd.register_config(config)
collectd.register_init(init)
collectd.register_shutdown(shutdown)
collectd.register_write(write)
