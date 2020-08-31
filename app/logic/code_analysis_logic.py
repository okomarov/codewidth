from collections import defaultdict
import math

from radon import metrics
from radon import raw
from radon import visitors
from radon.cli import Config
from radon.cli.harvest import Harvester
from radon.visitors import ComplexityVisitor
from radon.visitors import HalsteadVisitor

import utils


cfg = Config(
    ignore=None,
    exclude=None,
    include_ipynb=False,
    no_assert=False,
    off=True,
    multi=True)


def calculate_metrics(path, config=cfg):
    results = {}
    for k, result in CombinedHarvester([path], config).results:
        k = utils.remove_prefix(k, path)
        # Mongo does not like . in key names. Deal with multiple dots.
        parts = k.split('.')
        k = parts[0]
        ext = '.'.join(parts[1:])
        result.update({'meta': {'ext': ext}})
        results[k] = result
    return results


class CombinedHarvester(Harvester):
    def gobble(self, fobj):
        code = fobj.read()
        code_metrics = calculate_code_metrics(code)
        complexity = analyze_complexity(code, code_metrics, self.config.multi)
        return {**complexity, **code_metrics}


def analyze_complexity(code, code_metrics, is_multi):
    ast = visitors.code2ast(code)

    # Cyclomatic complexity
    complexity_visitor = ComplexityVisitor.from_ast(ast)
    res = get_wavg_complexity(complexity_visitor.blocks)

    # Maintainability index and rank
    if code_metrics['sloc'] != 0:
        comments_lines = (
            code_metrics['comments'] + (code_metrics['multi'] if is_multi else 0))
        comments = utils.divide_or_zero(comments_lines, code_metrics['sloc']) * 100
    else:
        comments = 0
    res['mi'] = metrics.mi_compute(
        calculate_halstead_volume(ast),
        complexity_visitor.total_complexity,
        code_metrics['lloc'],
        comments)

    return res


def get_wavg_complexity(blocks):
    total_block_len = 0
    complexity = 0
    for b in blocks:
        block_len = b.endline - b.lineno + 1
        complexity += b.complexity*block_len
        total_block_len += block_len

    return {
        'avg_complexity': utils.divide_or_zero(complexity, total_block_len),
        'total_block_len': total_block_len}


def calculate_code_metrics(code):
    '''Analyze the source code and return a namedtuple with the following
    fields:

        * **loc**: The number of lines of code (total)
        * **lloc**: The number of logical lines of code
        * **sloc**: The number of source lines of code (not necessarily
            corresponding to the LLOC)
        * **comments**: The number of Python comment lines
        * **multi**: The number of lines which represent multi-line strings
        * **single_comments**: The number of lines which are just comments with
            no code
        * **blank**: The number of blank lines (or whitespace-only ones)
        * **avg_ll**: The average legth of the lines of source codes

    The equation :math:`sloc + blanks + multi + single_comments = loc` should
    always hold.  Multiline strings are not counted as comments, since, to the
    Python interpreter, they are not comments but strings.
    '''
    if is_hardcoded_data(code):
        raise ValueError('SKIPPING. The file appears to be hardcoded data.')

    lloc = comments = single_comments = multi = blank = sloc = 0
    line_length = []
    lines = (line.strip() for line in code.splitlines())
    lineno = 1
    for line in lines:
        try:
            # Get a syntactically complete set of tokens that spans a set of
            # lines
            tokens, parsed_lines = raw._get_all_tokens(line, lines)
        except StopIteration:
            raise SyntaxError('SyntaxError at line: {0}'.format(lineno))

        lineno += len(parsed_lines)

        comments += sum(1 for t in tokens
                        if raw.TOKEN_NUMBER(t) == raw.tokenize.COMMENT)

        # Identify single line comments, conservatively
        if raw.is_single_token(raw.tokenize.COMMENT, tokens):
            single_comments += 1

        # Identify docstrings, conservatively
        elif raw.is_single_token(raw.tokenize.STRING, tokens):
            _, _, (start_row, _), (end_row, _), _ = tokens[0]
            if end_row == start_row:
                # Consider single-line docstrings separately from other
                # multiline docstrings
                single_comments += 1
            else:
                multi += sum(1 for line in parsed_lines if line)  # Skip empty lines
                blank += sum(1 for line in parsed_lines if not line)
        else:  # Everything else is either code or blank lines
            for parsed_line in parsed_lines:
                if parsed_line:
                    sloc += 1
                    line_length.append(len(parsed_line))
                else:
                    blank += 1

        # Process logical lines separately
        lloc += raw._logical(tokens)

    loc = sloc + blank + multi + single_comments
    return {
        'loc': loc, 'lloc': lloc, 'sloc': sloc, 'comments': comments,
        'multi': multi, 'blank': blank, 'single_comments': single_comments,
        'avg_ll': utils.divide_or_zero(sum(line_length), sloc)}


def is_hardcoded_data(code):
    lines_cutoff = 100
    ast_nodes = visitors.code2ast(code).body
    avg_code_len = sum(n.end_lineno-n.lineno+1 for n in ast_nodes)/len(ast_nodes)
    return avg_code_len > lines_cutoff


def calculate_halstead_volume(ast):
    visitor = HalsteadVisitor.from_ast(ast)
    h1, h2 = visitor.distinct_operators, visitor.distinct_operands
    N1, N2 = visitor.operators, visitor.operands
    h = h1 + h2
    N = N1 + N2
    return N * math.log(h, 2) if h != 0 else 0


def consolidate_repo_metrics(metrics):
    decimals = 2
    res = defaultdict(lambda: 0)
    total_compexity = 0
    total_line_length = 0
    total_mi = 0

    # Loop each file metrics
    res['num_files_error'] = 0
    for fname, m in metrics.items():
        if 'error' in m:
            res['num_files_error'] += 1
            continue

        # Cumulate directly
        res['total_block_len'] += m['total_block_len']
        res['loc'] += m['loc']
        res['lloc'] += m['lloc']
        res['sloc'] += m['sloc']
        res['comments'] += m['comments']
        res['multi'] += m['multi']
        res['blank'] += m['blank']
        res['single_comments'] += m['single_comments']
        res['multi'] += m['multi']

        # Cannot cumulate directly, get total numerator
        total_compexity += m['avg_complexity'] * m['total_block_len']
        total_line_length += m['avg_ll'] * m['sloc']
        total_mi += m['mi'] * m['loc']

        # Round to save space in json
        m['avg_complexity'] = round(m['avg_complexity'], decimals)
        m['mi'] = round(m['mi'], decimals)
        m['avg_ll'] = round(m['avg_ll'], decimals)

    # Repo level metrics
    res['num_files'] = len(metrics)
    res['avg_complexity'] = round(
        utils.divide_or_zero(total_compexity, res['total_block_len']),
        decimals)
    res['avg_mi'] = round(utils.divide_or_zero(total_mi, res['loc']), decimals)
    res['avg_ll'] = round(
        utils.divide_or_zero(total_line_length, res['sloc']),
        decimals)
    res['files'] = metrics

    return res
