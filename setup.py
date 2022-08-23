import setuptools

import os


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def read_requirements():
    """parses requirements from requirements.txt"""
    reqs_path = os.path.join(__location__, 'requirements.txt')
    with open(reqs_path, encoding='utf8') as f:
        reqs = [line.strip() for line in f if not line.strip().startswith('#')]

    names = []
    links = []
    for req in reqs:
        if '://' in req:
            links.append(req)
        else:
            names.append(req)
    return {'install_requires': names, 'dependency_links': links}


setuptools.setup(
    name='deeppavlov_agent',
    version='2.3.0a',
    include_package_data=True,
    description='An open source library, allowing you to create data processing systems based on a sequence graph, '
                'alongside with saving sample processing results in database.',
    long_description='An open source library, allowing you to create data processing systems based on a sequence '
                     'graph, alongside with saving sample processing results in database. '
                     'Possible application is chatbots or other NLP systems which combine multiple skills.',
    keywords=['chatbots', 'microservices', 'dialog systems', 'NLP'],
    packages=setuptools.find_packages(exclude=('docs',)),
    python_requires='>=3.7',
    data_files=[('.', ['deeppavlov_agent/settings.yaml'])],
    url="https://github.com/deepmipt/dp-agent",
    **read_requirements()
)
