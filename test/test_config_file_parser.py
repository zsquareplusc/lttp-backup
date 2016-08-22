
import io
import sys
import timeit
sys.path.append('..')


from link_to_the_past import config_file_parser

class Tester(config_file_parser.ControlFileParser):

    def __init__(self):
        self.count = 0

    def word_test(self):
        self.count += 1
        self.next_word()

    def test(self):
        self.count += 1
        self.next_word()

data = io.StringIO("test "*1000)
t = Tester()

print(min(timeit.repeat(
    stmt='data.seek(0); t.parse(config_file_parser.words_in_file("<test>", fileobj=data))',
    #~ setup='',
    number=100,
    globals={'Tester':Tester, 'config_file_parser':config_file_parser, 'data':data, 't':t})))

#~ print(t.count)
