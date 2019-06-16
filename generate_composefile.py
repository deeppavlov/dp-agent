import re
import yaml
import argparse
from pathlib import Path
from copy import deepcopy
from itertools import chain

from core.config import SKILLS, ANNOTATORS, SKILL_SELECTORS, RESPONSE_SELECTORS, POSTPROCESSORS, HOST, PORT

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--filename', type=str, default='docker-compose.yml')
parser.add_argument('-k', '--kuber', action='store_true')
parser.add_argument('-n', '--deploy-name', type=str, default='dpagent')
parser.add_argument('-r', '--repo-url', type=str, default='127.0.0.1:5000')
parser.add_argument('-c', '--cluster-ip', type=str, default='127.0.0.1')
parser.add_argument('-d', '--dns-ip', type=str, default='8.8.8.8')

AGENT_BASIC = {
    'agent': {'build': {'context': './', 'dockerfile': 'dockerfile_agent'},
              'container_name': 'agent',
              'volumes': ['.:/dp-agent'],
              'ports': ['8888:8888'],
              'tty': True,
              'depends_on': []}
}

MONGO_BASIC = {
    'mongo': {'command': 'mongod',
              'image': 'mongo:3.2.0',
              'ports': ['{}:27017'],
              # map port to none standard port, to avoid conflicts with locally installed mongodb.
              'volumes': ['/var/run/docker.sock:/var/run/docker.sock']}
}

SKILL_BASIC = {
    'build': {'context': './',
              'dockerfile': 'dockerfile_skill_basic',
              'args': {}},
    'volumes': ['.:/dp-agent',
                '${EXTERNAL_FOLDER}dp_logs:/logs',
                '${EXTERNAL_FOLDER}.deeppavlov:/root/.deeppavlov'],
    'ports': [],
    'tty': True,
}


class Config:
    def __init__(self, template):
        self.template = template
        if template is not None:
            self._config = deepcopy(template)


class AgentConfig(Config):
    def __init__(self, template=None):
        if template is None:
            template = deepcopy(AGENT_BASIC)
        else:
            template = deepcopy(template)

        super().__init__(template)

    def add_dependence(self, container_name):
        self._config['agent']['depends_on'].append(container_name)

    @property
    def config(self):
        return self._config


class SkillConfig(Config):
    def __init__(self, skill_config, template=None):
        if template is None:
            template = deepcopy(SKILL_BASIC)
        else:
            template = deepcopy(template)

        super().__init__(template)

        self.external = skill_config.get('external', False)
        self.container_name = None
        self.parse_config(skill_config)

    def parse_config(self, skill_config):
        self.container_name = skill_config['name']
        self.template['container_name'] = self.container_name
        self.template['build']['args']['skillport'] = skill_config['port']
        self.template['build']['args']['skillconfig'] = skill_config['path']
        self.template['ports'].append("{}:{}".format(skill_config['port'], skill_config['port']))

        # Ad-hoc workaraund for Kubernetes deployment
        if 'image' in skill_config.keys():
            self.template['image'] = skill_config['image']

    @property
    def config(self):
        return {self.container_name: self.template}


class DatabaseConfig:
    def __init__(self, host, port, template=None):
        if template is None and host == 'mongo':
            self.template = deepcopy(MONGO_BASIC)
            self.container_name = 'mongo'
            self.template['mongo']['ports'][0] = self.template['mongo']['ports'][0].format(port)
        else:
            self.template = deepcopy(template)
            self.container_name = None

    @property
    def config(self):
        return self.template


class DockerComposeConfig:
    def __init__(self, agent):
        self.agent = agent
        self.skills = []
        self.database = []

    def add_skill(self, skill):
        if skill.external is True:
            return
        self.skills.append(skill)
        self.agent.add_dependence(skill.container_name)

    def add_db(self, db):
        if not db.container_name:
            return
        self.database.append(db)
        self.agent.add_dependence(db.container_name)

    @property
    def config(self):
        config_dict = {'version': '2.0', 'services': {}}
        for container in chain([self.agent], self.skills, self.database):
            config_dict['services'].update(container.config)

        return dict(config_dict)

    @property
    def skills_config(self):
        config_dict = {'version': '2.0', 'services': {}}
        for container in self.skills:
            config_dict['services'].update(container.config)

        return dict(config_dict)

    @property
    def skills_list(self):
        return self.skills


class KuberDeployment:
    def __init__(self, deployment_name, container_name, repo_url, container_port, cluster_port,
                 cluster_ip, dns_ip='8.8.8.8'):

        deployment_name = re.sub('[^-0-9a-zA-Z]+', '-', deployment_name)
        container_name = re.sub('[^-0-9a-zA-Z]+', '-', container_name)

        self.dp_template = {
            'apiVersion': 'apps/v1beta1',
            'kind': 'Deployment',
            'metadata': {'name': f'{deployment_name}-{container_name}-dp'},
            'spec': {
                'replicas': 1,
                'template': {
                    'metadata': {'labels': {'app': f'{deployment_name}-{container_name}-dp'}},
                    'spec': {
                        'containers': [
                            {'name': 'agent-skill',
                             'image': f'{repo_url}/{container_name}',
                             'ports': [
                                 {'name': 'cs-port',
                                  'protocol': 'TCP',
                                  'containerPort': container_port}
                             ]}
                        ],
                        'dnsPolicy': 'None',
                        'dnsConfig': {'nameservers': [dns_ip]}
                    }
                }
            }
        }
        self.dp_file_name = f'{deployment_name}_{container_name}_dp.yaml'

        self.lb_template = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {'name': f'{deployment_name}-{container_name}-lb'},
            'spec': {
                'selector': {'app': f'{deployment_name}-{container_name}-dp'},
                'type': 'LoadBalancer',
                'externalIPs': [str(cluster_ip)],
                'ports': [
                    {'name': 'cluster-skill-port',
                     'protocol': 'TCP',
                     'port': cluster_port,
                     'targetPort': 'cs-port'}
                ]
            }
        }
        self.lb_file_name = f'{deployment_name}_{container_name}_lb.yaml'

    @property
    def dp_config(self):
        return self.dp_template

    @property
    def dp_filename(self):
        return self.dp_file_name

    @property
    def lb_config(self):
        return self.lb_template

    @property
    def lb_filename(self):
        return self.lb_file_name


class KuberMongoDeployment(KuberDeployment):
    def __init__(self, deployment_name, container_name, cluster_port, cluster_ip, dns_ip='8.8.8.8'):
        container_port = 27017
        repo_url = ''
        super().__init__(deployment_name, container_name, repo_url, container_port, cluster_port, cluster_ip, dns_ip)
        self.dp_template['spec']['template']['spec']['containers'][0]['image'] = 'mongo:3.2.0'


class KuberConfig:
    def __init__(self, dc_config: DockerComposeConfig, deployment_name, repo_url, cluster_ip, dns_ip='8.8.8.8'):
        self.deployments = []

        for skill in dc_config.skills_list:
            skill_config = list(skill.config.values())[0]

            self.deployments.append(KuberDeployment(deployment_name,
                                                    skill.container_name,
                                                    repo_url,
                                                    skill_config['build']['args']['skillport'],
                                                    skill_config['build']['args']['skillport'],
                                                    cluster_ip,
                                                    dns_ip))

        self.deployments.append(KuberMongoDeployment(deployment_name,
                                                     'mongo',
                                                     PORT,
                                                     cluster_ip,
                                                     dns_ip))

    @property
    def deployments_list(self):
        return self.deployments


if __name__ == '__main__':
    args = parser.parse_args()

    dcc = DockerComposeConfig(AgentConfig())

    for conf in chain(SKILLS, ANNOTATORS, SKILL_SELECTORS, RESPONSE_SELECTORS, POSTPROCESSORS):
        # Ad-hoc workaraund for Kubernetes deployment
        if args.kuber:
            conf['image'] = f'{args.repo_url}/{conf["name"]}'

        dcc.add_skill(SkillConfig(conf))

    dcc.add_db(DatabaseConfig(HOST, PORT))

    if args.kuber:
        kubec = KuberConfig(dcc, args.deploy_name, args.repo_url, args.cluster_ip, args.dns_ip)
        configs_dir = Path('.').resolve() / 'kuber_cofigs'
        configs_dir.mkdir(exist_ok=True)

        for deployment in kubec.deployments_list:
            dp_config_path = configs_dir / deployment.dp_filename
            lb_config_path = configs_dir / deployment.lb_filename

            with dp_config_path.open('w') as f_dp:
                yaml.dump(deployment.dp_config, f_dp)

            with lb_config_path.open('w') as f_lb:
                yaml.dump(deployment.lb_config, f_lb)

        with open(args.filename, 'w') as f:
            yaml.dump(dcc.skills_config, f)
    else:
        with open(args.filename, 'w') as f:
            yaml.dump(dcc.config, f)

