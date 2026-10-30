import unittest

from protocol_generator import ProtocolGenerator


class DummyClient:
    api_key = 'test_key'

    def __init__(self):
        self.content = None
        self.messages = None

    def create_message_anthropic_format(self, content, max_tokens, temperature):
        self.content = content
        return 'Протокол'

    def create_message(self, messages, max_tokens, temperature):
        self.messages = messages
        return 'Протокол'


class DummyTemplates:
    @staticmethod
    def wrap_transcript(transcript):
        return f'<transcript>{transcript}</transcript>'

    @staticmethod
    def wrap_protocol_template(structure):
        return f'<protocol_template>{structure}</protocol_template>'


class TestProtocolGeneratorParticipants(unittest.TestCase):
    def setUp(self):
        self.generator = ProtocolGenerator.__new__(ProtocolGenerator)
        self.generator.client = DummyClient()
        self.generator.model = 'test-model'
        self.generator.openrouter_model = 'test-model'
        self.participants = [{
            'full_name': 'Иван Петров',
            'company': 'ООО Пример',
            'position': 'Руководитель проекта'
        }]

    def test_participants_are_added_to_flat_prompt(self):
        self.generator.generate_meeting_summary(
            'Спикер 0: Рассмотрим план проекта',
            participants=self.participants
        )

        self.assertIn('Иван Петров', self.generator.client.content)
        self.assertIn('ООО Пример', self.generator.client.content)
        self.assertIn('Руководитель проекта', self.generator.client.content)
        self.assertIn('Сопоставь обозначения спикеров', self.generator.client.content)

    def test_participants_are_added_to_structured_messages(self):
        parts = {
            'base_prompt': 'Создай протокол',
            'protocol_structure': 'Участники и решения',
            'final_instruction': 'Не выдумывай факты',
            'meta': ''
        }

        messages = self.generator._build_structured_messages(
            DummyTemplates(), parts, 'Спикер 0: Рассмотрим план проекта', self.participants
        )

        instructions = messages[1]['content'][1]['text']
        self.assertIn('Иван Петров', instructions)
        self.assertIn('ООО Пример', instructions)
        self.assertIn('Руководитель проекта', instructions)
        self.assertIn('Сопоставь обозначения спикеров', instructions)

    def test_participants_are_added_to_all_template_types(self):
        from meeting_templates import MeetingTemplates

        templates = MeetingTemplates()
        template_types = templates.get_available_templates()['all'] + ['auto']
        for template_type in template_types:
            with self.subTest(template_type=template_type):
                self.generator.client = DummyClient()
                result = self.generator.generate_meeting_summary(
                    'Спикер 0: Рассмотрим план проекта',
                    template_type=template_type,
                    templates_system=templates,
                    participants=self.participants
                )

                self.assertEqual(result, 'Протокол')
                if self.generator.client.content is not None:
                    prompt = self.generator.client.content
                else:
                    prompt = '\n'.join(
                        block.get('text', '')
                        for message in self.generator.client.messages
                        for block in message['content']
                    )
                self.assertIn('Иван Петров', prompt)
                self.assertIn('ООО Пример', prompt)
                self.assertIn('Руководитель проекта', prompt)
                self.assertIn('Сопоставь обозначения спикеров', prompt)
                self.assertIn('Если соответствие подтверждается транскриптом', prompt)

    def test_empty_participants_do_not_add_identification_context(self):
        for participants in (None, []):
            with self.subTest(participants=participants):
                self.generator.client = DummyClient()
                self.generator.generate_meeting_summary(
                    'Спикер 0: Рассмотрим план проекта',
                    participants=participants
                )

                self.assertNotIn('ДАННЫЕ ОБ УЧАСТНИКАХ ВСТРЕЧИ', self.generator.client.content)
                self.assertNotIn('Сопоставь обозначения спикеров', self.generator.client.content)


if __name__ == '__main__':
    unittest.main()
