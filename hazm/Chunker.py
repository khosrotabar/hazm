# coding: utf-8

"""این ماژول شامل کلاس‌ها و توابعی برای تجزیهٔ متن به عبارات اسمی، فعلی و حرف
اضافه‌ای است. **میزان دقت تجزیه‌گر سطحی در نسخهٔ حاضر ۸۹.۹ درصد [^1] است.**
[^1]:
این عدد با انتشار هر نسخه بروزرسانی می‌شود.

"""

from __future__ import unicode_literals
from nltk.chunk import RegexpParser, tree2conlltags, conlltags2tree
from nltk.tree import Tree
from .SequenceTagger import IOBTagger, prepare_data_IOB


def tree2brackets(tree):
    """خروجی درختی تابع [parse()][hazm.Chunker.Chunker.parse] را به یک ساختار
    کروشه‌ای تبدیل می‌کند.
    
    Examples:
        >>> chunker = Chunker(model='resources/chunker.model')
        >>> tree=chunker.parse([('نامه', 'Ne'), ('ایشان', 'PRO'), ('را', 'POSTP'), ('دریافت', 'N'), ('داشتم', 'V'), ('.', 'PUNC')])
        >>> print(tree)
        (S
          (NP نامه/Ne ایشان/PRO)
          (POSTP را/POSTP)
          (VP دریافت/N داشتم/V)
          ./PUNC)
        >>> tree2brackets(tree)
        '[نامه ایشان NP] [را POSTP] [دریافت داشتم VP] .'
    
    Args:
        tree (str): ساختار درختی حاصل از پردزاش تابع parse()
    
    Returns:
        (str): رشته‌ای از کروشه‌ها که در هر کروشه جزئی از متن به همراه نوع آن جای گرفته است.
    
    """
    str, tag = "", ""
    for item in tree2conlltags(tree):
        if item[2][0] in {"B", "O"} and tag:
            str += tag + "] "
            tag = ""

        if item[2][0] == "B":
            tag = item[2].split("-")[1]
            str += "["
        str += item[0] + " "

    if tag:
        str += tag + "] "

    return str.strip()

def tree2IOB(tree):
    boi_tags = []
    for subtree in tree:
        if isinstance(subtree, Tree):
            chunk_label = subtree.label()
            words = [word for word, pos in subtree.leaves()]
            for i, word in enumerate(words):
                if i == 0:
                    boi_tags.append((word, subtree[i][1], f"B-{chunk_label}"))
                else:
                    boi_tags.append((word, subtree[i][1], f"I-{chunk_label}"))
        else:
            boi_tags.append((subtree[0], subtree[1], 'O'))
    return boi_tags


class Chunker(IOBTagger):
    """این کلاس شامل توابعی برای تقطیع متن، آموزش و ارزیابی مدل است.
    
    """

    def train(self, trees, c1=0.4, c2=0.04, max_iteration=400, verbose=True, file_name='chunker_crf.model', data_maker=prepare_data_IOB, report_duration=True):
        """از روی درخت ورودی، مدل را آموزش می‌دهد.
        
        Args:
            trees (List[Tree]): لیستی از درخت‌ها برای آموزش مدل.
        
        """
        return super().train([tree2IOB(tree) for tree in trees], c1, c2, max_iteration, verbose, file_name, data_maker, report_duration)

    def parse(self, sentence, data_provider = prepare_data_IOB):
        """جمله‌ای را در قالب لیستی از تاپل‌های دوتایی [(توکن, نوع), (توکن, نوع), ...]
        دریافت می‌کند و درخت تقطع‌شدهٔ آن را بر می‌گرداند.
        
        Examples:
            >>> chunker = Chunker(model='resources/chunker.model')
            >>> tree=chunker.parse([('نامه', 'Ne'), ('ایشان', 'PRO'), ('را', 'POSTP'), ('دریافت', 'N'), ('داشتم', 'V'), ('.', 'PUNC')])
            >>> print(tree)
            (S
              (NP نامه/Ne ایشان/PRO)
              (POSTP را/POSTP)
              (VP دریافت/N داشتم/V)
              ./PUNC)
        
        Args:
            sentence (List[Tuple[str,str]): جمله‌ای که باید درخت تقطیع‌شدهٔ آن تولید شود.
        
        Returns:
            (str): ساختار درختی حاصل از تقطیع.
            برای تبدیل این ساختار درختی به یک ساختار کروشه‌ای و قابل‌درک‌تر
            می‌توانید از تابع `tree2brackets()` استفاده کنید.
        
        """
        return conlltags2tree(super().tag(sentence, data_provider))

    def parse_sents(self, sentences, data_maker = prepare_data_IOB):
        """جملات ورودی را به‌شکل تقطیع‌شده و در قالب یک برمی‌گرداند.
        
        Args:
            sentences (List[List[Tuple(str,str)]]): جملات ورودی.
        
        Yields:
            (Iterator[str]): یک `Iterator` از جملات تقطیع شده.
        
        """
        for conlltagged in super(Chunker, self).tag_sents(sentences, data_maker):
            yield conlltags2tree(conlltagged)


class RuleBasedChunker(RegexpParser):
    """
    
    Examples:
        >>> chunker = RuleBasedChunker()
        >>> tree2brackets(chunker.parse([('نامه', 'Ne'), ('۱۰', 'NUMe'), ('فوریه', 'Ne'), ('شما', 'PRO'), ('را', 'POSTP'), ('دریافت', 'N'), ('داشتم', 'V'), ('.', 'PUNC')]))
        '[نامه ۱۰ فوریه شما NP] [را POSTP] [دریافت داشتم VP] .'
    
    """

    def __init__(self):
        grammar = r"""

            NP:
                <P>{<N>}<V>

            VP:
                <.*[^e]>{<N>?<V>}
                {<V>}

            ADVP:
                {<ADVe?><AJ>?}

            ADJP:
                <.*[^e]>{<AJe?>}

            NP:
                {<DETe?|Ne?|NUMe?|AJe|PRO|CL|RESe?><DETe?|Ne?|NUMe?|AJe?|PRO|CL|RESe?>*}
                <N>}{<.*e?>

            ADJP:
                {<AJe?>}

            POSTP:
                {<POSTP>}

            PP:
                {<Pe?>+}

        """

        super(RuleBasedChunker, self).__init__(grammar=grammar)
