import sys, os, unittest

# Extend PYTHONPATH with local 'lib' folder
jasyroot = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir, "lib"))
sys.path.insert(0, jasyroot)

import jasy.js.parse.Parser as Parser
from jasy.js.MetaData import MetaData

class TestMetaData(unittest.TestCase):
    def process(self, code):
        node = Parser.parse(code)
        metadata = MetaData(node)
        return metadata

    def test_name(self):

        md = self.process("""

        /**
          * @name {document.retrieveSelector}
         */

        document.retrieveSelector = (function (filter) {

	}([].filter));

        """)

        self.assertEqual(md.name, 'document.retrieveSelector')

    def test_require(self):

        md = self.process("""

        /**
         * @require {core.detect.Platform}
         */
	core.Module("core.detect.System", {
		VALUE: name + " " + version
	});

        """)

        self.assertEqual(set(md.requires), set(['core.detect.Platform']))

    def test_break(self):

        md = self.process("""

        /**
         * @break {core.Env}
         */
        (function(global, undef)
        {
        })(this);

        """)

        self.assertEqual(set(md.breaks), set(['core.Env']))

    def test_asset(self):

        md = self.process("""

        /**
         * @asset {mynamespace/*}
         * @asset {externallib/*}
         */
        core.Module("mynamespace.App", {

        });

        """)

        self.assertEqual(set(md.assets), set(['mynamespace/*', 'externallib/*']))

    def test_optional(self):

        md = self.process("""

        /**
         * @optional {optional.a}
         * @optional {optional.b}
         */
        core.Module("mynamespace.App", {

        });

        """)

        self.assertEqual(set(md.optionals), set(['optional.a', 'optional.b']))


if __name__ == '__main__':
    tests = unittest.TestLoader().loadTestsFromTestCase(TestMetaData)
    unittest.TextTestRunner(verbosity=1).run(tests)
