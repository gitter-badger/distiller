import sys
import click

import _distiller_common

UTIL_NAME = 'pairsam_select'

@click.command()
@click.argument(
    'field',
    metavar='FIELD',
    type=click.Choice(['pair_type', 'chrom1', 'chrom2', 'read_id']),
)

@click.argument(
    'value', 
    metavar='VALUE',
)

@click.option(
    '--match-method', 
    type=click.Choice(['comma_list', 'single_value', 'wildcard', 'regexp']),
    default='comma_list',
    help='The method of matching of a field to `value`. Possible choices '
        'are: comma_list (`value` is interpreted as a comma-separated list of accepted values), '
        'single_value, wildcard, regexp (a Python-flavor regular expression).',
    show_default=True,
)

@click.option(
    '--input',
    type=str, 
    default="",
    help='input pairsam file.'
        ' If the path ends with .gz, the input is gzip-decompressed.'
        ' By default, the input is read from stdin.')

@click.option(
    "--output", 
    type=str, 
    default="", 
    help='output file.'
        ' If the path ends with .gz, the output is bgzip-compressed.'
        ' By default, the output is printed into stdout.')

@click.option(
    "--output-rest", 
    type=str, 
    default="", 
    help='output file for pairs of other types. '
        ' If the path ends with .gz, the output is bgzip-compressed.'
        ' By default, such pairs are dropped.')

@click.option(
    "--send-comments-to", 
    type=click.Choice(['selected', 'rest', 'both', 'none']),
    default="both", 
    help="Which of the outputs should receive header and comment lines",
    show_default=True)

def select(
    field, value, match_method,input,output, output_rest, send_comments_to
    ):
    '''Read a pairsam file and print only the pairs of a certain type(s).

    FIELD : The field to filter pairs by. Possible choices are: pair_type,
    chrom1,chrom2,read_id.

    VALUE : Select reads with FIELD matching VALUE. Depending on 
    --match-method, this argument can be interpreted as a single value, 
    a comma separated list, a wildcard or a regexp.
    '''
    
    instream = (_distiller_common.open_bgzip(input, mode='r') 
                if input else sys.stdin)
    outstream = (_distiller_common.open_bgzip(output, mode='w') 
                 if output else sys.stdout)
    outstream_rest = (_distiller_common.open_bgzip(output_rest, mode='w') 
                      if output_rest else None)

    colidx = {
        'chrom1':_distiller_common.COL_C1,
        'chrom2':_distiller_common.COL_C2,
        'read_id':_distiller_common.COL_READID,
        'pair_type':_distiller_common.COL_PTYPE,
        }[field]

    if match_method == 'single_value':
        do_match = lambda x: x==value
    elif match_method == 'comma_list':
        vals = value.split(',')
        do_match = lambda x: any((i==x for i in vals))
    elif match_method == 'wildcard':
        import fnmatch, re
        regex = fnmatch.translate(value)
        reobj = re.compile(regex)
        do_match = lambda x: bool(reobj.match(x))
    elif match_method == 'regexp':
        import re
        reobj = re.compile(value)
        do_match = lambda x: bool(reobj.match(x))
    else:
        raise Exception('An unknown matching method: {}'.format(match_method))

    header, pairsam_body_stream = _distiller_common.get_header(instream)
    header = _distiller_common.append_pg_to_sam_header(
        header,
        {'ID': UTIL_NAME,
         'PN': UTIL_NAME,
         'VN': _distiller_common.DISTILLER_VERSION,
         'CL': ' '.join(sys.argv)
         })

    outstream.writelines(header)
    if outstream_rest:
        outstream.writelines(header)

    for line in pairsam_body_stream:
        cols = line.split('\v')
        if do_match(cols[colidx]):
            outstream.write(line)
        elif outstream_rest:
            outstream_rest.write(line)

    if hasattr(instream, 'close'):
        instream.close()
    if hasattr(outstream, 'close'):
        outstream.close()
    if outstream_rest:
        outstream_rest.close()

if __name__ == '__main__':
    select()
