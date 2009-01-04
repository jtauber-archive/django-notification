from distutils.core import setup

setup(
    name='django-notification',
    version=__import__('notification').__version__,
    description='Many sites need to notify users when certain events have occurred and to allow configurable options as to how those notifications are to be received. The project aims to provide a Django app for this sort of functionality.',
    long_description=open('docs/index.txt').read(),
    author='James Tauber',
    author_email='jtauber@jtauber.com',
    url='http://code.google.com/p/django-notification/',
    packages=[
        'notification',
        'notification.management',
        'notification.management.commands',
        'notification.templatetags',
    ],
    package_dir={'notification': 'notification'},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
