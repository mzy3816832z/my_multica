"""
命令行发送系统通知

用法：
    python manage.py send_system_notification --title "系统维护通知" --content "..." [--role landlord] [--user-id 1]
"""
from django.core.management.base import BaseCommand, CommandError

from apps.messages_app.models import Message
from apps.users.models import User


class Command(BaseCommand):
    help = '向用户发送系统通知站内信（type=system）'

    def add_arguments(self, parser):
        parser.add_argument('--title', required=True, help='通知标题')
        parser.add_argument('--content', required=True, help='通知内容')
        parser.add_argument(
            '--role',
            choices=['tenant', 'landlord', 'admin'],
            help='目标角色，不传则发送给全部用户',
        )
        parser.add_argument('--user-id', type=int, help='指定单个用户 ID')

    def handle(self, *args, **options):
        title = options['title'].strip()
        content = options['content'].strip()
        if not title or not content:
            raise CommandError('title 与 content 不能为空')

        users = User.all_objects.filter(is_active=True)
        if options['role']:
            users = users.filter(role=options['role'])
        if options['user_id']:
            users = users.filter(id=options['user_id'])

        count = 0
        for user in users:
            Message.objects.create(
                user=user,
                type='system',
                title=title,
                content=content,
                related_apartment=None,
                related_audit=None,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'已向 {count} 名用户发送系统通知'))
