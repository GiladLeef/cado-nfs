import os
import subprocess
import sys
import argparse
import concurrent.futures
import copy
import hashlib
import re

from .general_class import GeneralClass
from .descent_upper_class import DescentUpperClass
from .descent_middle_class import DescentMiddleClass
from .descent_lower_class import DescentLowerClass
from .descent_utils import drive_me_crazy, feature_set_hwloc
from .descent_utils import FailedDescent, InconsistentDescent


def _make_parser():
    parser = argparse.ArgumentParser(
        prog='descent',
        description="Descent initialization for DLP")

    # Required
    parser.add_argument("--target",
                        help="Element whose DL is wanted",
                        type=str,
                        required=True)
    parser.add_argument("--target-name",
                        help=argparse.SUPPRESS,
                        type=str)
    parser.add_argument("--timestamp",
                        help="Prefix all lines with a time stamp",
                        action="store_true")

    GeneralClass.declare_args(parser)
    DescentUpperClass.declare_args(parser)
    DescentMiddleClass.declare_args(parser)
    DescentLowerClass.declare_args(parser)
    return parser


def _run_one_descent(args):
    """Run one target using the current Python process.

    The target-specific state is constructed locally.  The external tools
    used by the descent (las and sm_simple) remain unchanged, but there is no
    Python subprocess per target.
    """
    general = GeneralClass(args)

    if general.target() == 1:
        # the re-randomization does not work for target=1
        print("# p=%d" % general.p())
        print("# ell=%d" % general.ell())
        print("# target=%s" % args.target)
        print("log(target)=0")
    else:
        init = DescentUpperClass(general, args)
        middle = DescentMiddleClass(general, args)
        lower = DescentLowerClass(general, args)

        if general.has_rational_side() and init.external is None:
            seed = 42
            while True:
                try:
                    todofile, initial_split, firstrelsfile, _ = \
                        init.do_descent_for_real(general.target(), seed)
                    if todofile is None:
                        seed += 1
                        continue
                    relsfile = middle.do_descent(todofile, seed)
                    lower.do_descent([relsfile], initial_split)
                    break
                except (FailedDescent, InconsistentDescent) as e:
                    print("Descent attempt with seed %d failed: %s"
                          % (seed, e))
                    print("Trying again with another random seed...")
                    seed += 1
        else:
            todofile, initial_split, firstrelsfile = \
                init.do_descent(general.target())
            relsfile = middle.do_descent(todofile)
            if firstrelsfile:
                lower.do_descent([firstrelsfile, relsfile], initial_split)
            else:
                lower.do_descent([relsfile], initial_split)

    general.cleanup()


def _split_targets(target, extdeg):
    # For GF(p), comma-separated values are independent targets.  For an
    # extension field, commas are the coefficients of one target; semicolons
    # separate multiple extension-field targets.
    if extdeg == 1:
        return target.split(",")
    return target.split(";")


def run_targets(args, targets, runner=_run_one_descent):
    """Run target descents in this process, using worker threads."""
    workers = max(1, min(int(args.threads), len(targets)))

    def run_target(index, target):
        target_args = copy.copy(args)
        target_args.target = target
        target_args.target_name = "target-" + hashlib.sha256(
            str(target).encode("utf-8")).hexdigest()[:16]
        return runner(target_args)

    if len(targets) == 1 or workers == 1:
        return [run_target(index, target)
                for index, target in enumerate(targets)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_target, index, target)
                   for index, target in enumerate(targets)]
        return [future.result() for future in futures]


def descent_main():
    # Parse command line arguments
    parser = _make_parser()

    args = parser.parse_args()

    sys.stdout = drive_me_crazy(sys.stdout, args.timestamp)

    las_bin = os.path.join(args.cadobindir, "sieve", "las")
    cp = subprocess.Popen([ las_bin, "-help" ],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)

    feature_set_hwloc(not bool(re.search(r"unused, needs hwloc",
                                         cp.stderr.read().decode())))
    extdeg = args.gfpext if args.gfpext is not None else 1
    targets = _split_targets(args.target, extdeg)
    run_targets(args, targets)
