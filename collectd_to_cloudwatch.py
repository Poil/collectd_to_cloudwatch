import collectd
import boto.ec2.cloudwatch
import boto.ec2
import boto.utils
import sys
from yaml import load as yload
from xml.dom.minidom import parseString

REGION = False
AWS_ACCESS_KEY_ID = False
AWS_SECRET_ACCESS_KEY = False
NAMESPACE = "AWS/EC2"
METRICS = {}
cw_ec2 = None
ec2 = None
INSTANCE_ID = False
AS_GRP_NAME = False


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


def get_tag():
    global ec2, INSTANCE_ID
    reservations = ec2.get_all_instances(instance_ids=[INSTANCE_ID])
    instance = reservations[0].instances[0]
    if instance.tags.get('aws:autoscaling:groupName', False):
        return instance.tags['aws:autoscaling:groupName'].encode('ascii')
    else:
        return False


def init():
    collectd.debug('initing stuff')
    global ec2, cw_ec2, REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AS_GRP_NAME
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        try:
            ec2 = boto.ec2.connect_to_region(REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            cw_ec2 = boto.ec2.cloudwatch.connect_to_region(REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        except:
            collectd.warning("Couldn't connect to cloudwatch with your access_key")
    else:
        try:
            ec2 = boto.ec2.connect_to_region(REGION)
            cw_ec2 = boto.ec2.cloudwatch.connect_to_region(REGION)
        except:
            collectd.warning("Couldn't connect to cloudwatch with your instance role")

    AS_GRP_NAME = get_tag()


def shutdown():
    collectd.debug('Shutting down collectd_to_cloudwatch plugin')


def write(vl, datas=None):
    global cw_ec2, NAMESPACE, METRICS, INSTANCE_ID, AS_GRP_NAME

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
            try:
                collectd.debug(('Putting {metric}={value} {unit} to {namespace} {dimensions}').format(metric=metric_name, value=i, unit=unit, namespace=NAMESPACE, dimensions=dimensions))
                cw_ec2.put_metric_data(namespace=NAMESPACE, name=metric_name, value=float(i), unit=unit, dimensions=dimensions)
                if AS_GRP_NAME:
                    dimensions = {'AutoScalingGroupName': AS_GRP_NAME}
                    collectd.debug(('Putting {metric}={value} {unit} to {namespace} {dimensions}').format(metric=metric_name, value=i, unit=unit, namespace=NAMESPACE, dimensions=dimensions))
                    cw_ec2.put_metric_data(namespace=NAMESPACE, name=metric_name, value=float(i), unit=unit, dimensions=dimensions)
            except boto.exception.EC2ResponseError:
                print_boto_error()
                collectd.warning(('Fail to put {metric}={value} {unit} to {namespace} {dimensions}').format(metric=metric_name, value=i, unit=unit, namespace=NAMESPACE, dimensions=dimensions))


def print_boto_error():
    """Attempts to extract the XML from boto errors to present plain errors with no stacktraces."""

    try:
        quick_summary, null, xml = str(sys.exc_info()[1]).split('\n')
        error_msg = parseString(xml).getElementsByTagName('Response')[0].getElementsByTagName('Errors')[0].getElementsByTagName('Error')[0]
        print
        collectd.warning('AWS Error: {0}\n'.format(quick_summary))
        collectd.warning('{0}: {1}\n'.format(error_msg.getElementsByTagName('Code')[0].firstChild.data, error_msg.getElementsByTagName('Message')[0].firstChild.data))
        print
    except:
        # Raise the exception if parsing failed
        raise
    return False


collectd.register_config(config)
collectd.register_init(init)
collectd.register_shutdown(shutdown)
collectd.register_write(write)
