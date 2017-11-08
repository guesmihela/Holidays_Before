
{
    'name': 'Holiday_Before',
    'version': '0.1.0.0',
    'sequence' : 0,
    'category': 'Human Resources',
    'license': 'AGPL-3',
    'summary': 'demande de congé doit être  avant un nombre de jours bien determiné',
    'author': 'TNT',
    'website': 'http://tnt.com.tn',
    'depends': ['hr_holidays'],
    'active': True,
    'data': [
        'views/hr_holidays_status.xml',
        'views/hr_holidays.xml',
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}
