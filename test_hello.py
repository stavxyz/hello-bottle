
import unittest


class TestHello(unittest.TestCase):

    def test_it_now(self):

        self.assertEqual(42, 42)


if __name__ == '__main__':
    unittest.main()
