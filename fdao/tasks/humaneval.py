"""HumanEval coding tasks with sandboxed subprocess execution."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from dataclasses import dataclass

from fdao.tasks.base import Task
from fdao.types import Difficulty, TaskCategory, ValidationResult

EXECUTION_TIMEOUT = 10  # seconds


@dataclass
class HumanEvalTask(Task):
    """A single HumanEval problem.

    The agent sees the function signature + docstring (prompt).
    validate() appends the test cases and runs the whole thing in a subprocess.
    """

    task_id: str
    _prompt: str
    test_code: str
    entry_point: str
    category: TaskCategory = TaskCategory.CODE_GENERATION
    difficulty: Difficulty = Difficulty.MEDIUM

    @property
    def prompt(self) -> str:
        return self._prompt

    def validate(self, attempt: str) -> ValidationResult:
        """Extract code from attempt, run tests in a subprocess, return result."""
        code = _extract_code(attempt)
        full_script = f"{code}\n\n{self.test_code}\n\ncheck({self.entry_point})\n"

        try:
            result = subprocess.run(
                [sys.executable, "-c", full_script],
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT,
            )
            if result.returncode == 0:
                return ValidationResult(passed=True, score=1.0)
            return ValidationResult(
                passed=False,
                score=0.0,
                details=result.stderr[:500] or result.stdout[:500],
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(passed=False, score=0.0, details="Execution timed out")
        except Exception as e:
            return ValidationResult(passed=False, score=0.0, details=str(e))


def _extract_code(attempt: str) -> str:
    """Pull Python code out of the attempt string.

    Handles three cases:
    1. Fenced code block  ```python ... ```
    2. Fenced code block  ``` ... ```
    3. Raw code (no fences)
    """
    if "```" in attempt:
        blocks = attempt.split("```")
        for i, block in enumerate(blocks):
            if i % 2 == 1:  # odd indices are inside fences
                code = block.lstrip("python").lstrip("py").strip()
                if code:
                    return code
    return attempt.strip()


# ---------------------------------------------------------------------------
# Starter set — 10 HumanEval problems for the Phase 1 milestone run
# These are a representative sample from the public HumanEval benchmark.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Hard set — problems where llama-3.3-70b fails on first attempt
# These have multi-step logic, edge cases, or non-obvious algorithms.
# This is the set that produces interesting trajectories for research.
# ---------------------------------------------------------------------------

HUMANEVAL_HARD: list[HumanEvalTask] = [
    HumanEvalTask(
        task_id="HE/H1",
        _prompt=textwrap.dedent("""\
            def sort_third(l: list):
                \"\"\"This function takes a list l and returns a list l' such that
                l' is identical to l in the indicies that are not divisible by three,
                while its values at the indicies that are divisible by three are equal
                to the values of the corresponding indicies of l, but sorted.

                >>> sort_third([1, 2, 3])
                [1, 2, 3]
                >>> sort_third([5, 6, 3, 4, 8, 9, 2])
                [2, 6, 3, 4, 8, 9, 5]
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert tuple(candidate([1, 2, 3])) == tuple([1, 2, 3])
                assert tuple(candidate([5, 6, 3, 4, 8, 9, 2])) == tuple([2, 6, 3, 4, 8, 9, 5])
                assert tuple(candidate([5, 3, -5, 2, -3, 3, 9, 0, 123, 1, -10])) == tuple([1, 3, -5, 2, -3, 3, 5, 0, 123, 9, -10])
                assert tuple(candidate([5, 8, -12, 4, 23, 2, 3, 11, 12, -10])) == tuple([-10, 8, -12, 3, 23, 2, 4, 11, 12, 5])
        """),
        entry_point="sort_third",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H2",
        _prompt=textwrap.dedent("""\
            def encode_cyclic(s: str):
                \"\"\"
                returns encoded string by cycling groups of three characters.
                \"\"\"
                groups = [s[(3 * i):min((3 * i + 3), len(s))] for i in range((len(s) + 2) // 3)]
                groups = [(group[1:] + group[0]) if len(group) == 3 else group for group in groups]
                return "".join(groups)

            def decode_cyclic(s: str):
                \"\"\"
                takes as input string encoded with encode_cyclic function. Returns decoded string.
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def encode_cyclic(s):
                groups = [s[(3 * i):min((3 * i + 3), len(s))] for i in range((len(s) + 2) // 3)]
                groups = [(group[1:] + group[0]) if len(group) == 3 else group for group in groups]
                return "".join(groups)

            def check(candidate):
                from random import randint, choice, seed
                import string
                seed(42)
                letters = string.ascii_lowercase
                for _ in range(100):
                    s = ''.join(choice(letters) for i in range(randint(1, 30)))
                    assert candidate(encode_cyclic(s)) == s, f"Failed on: {s!r}"
        """),
        entry_point="decode_cyclic",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H3",
        _prompt=textwrap.dedent("""\
            def next_smallest(lst):
                \"\"\"
                You are given a list of integers.
                Write a function next_smallest() that returns the 2nd smallest element of the list.
                Return None if there is no such element.

                next_smallest([1, 2, 3, 4, 5]) == 2
                next_smallest([5, 1, 4, 3, 2]) == 2
                next_smallest([]) == None
                next_smallest([1, 1]) == None
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([1, 2, 3, 4, 5]) == 2
                assert candidate([5, 1, 4, 3, 2]) == 2
                assert candidate([]) == None
                assert candidate([1, 1]) == None
                assert candidate([1,1,1,1,0]) == 1
                assert candidate([1, 0**0]) == None
                assert candidate([-35, 34, 12, -45]) == -35
        """),
        entry_point="next_smallest",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H4",
        _prompt=textwrap.dedent("""\
            def is_bored(S):
                \"\"\"
                You'll be given a string of words, and your task is to count the number
                of boredoms. A boredom is a sentence whose FIRST WORD is exactly the
                pronoun "I" (case-sensitive, not just starting with the letter I).
                "Is the sky blue?" does NOT count — "Is" starts with I but is not the word "I".
                Sentences are delimited by '.', '?' or '!'.

                For example:
                >>> is_bored("Hello world")
                0
                >>> is_bored("Is the sky blue?")
                0
                >>> is_bored("I love It !")
                1
                >>> is_bored("The sky is blue. The sun is shining. I love this weather")
                1
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate("Hello world") == 0
                assert candidate("Is the sky blue?") == 0
                assert candidate("I love It !") == 1
                assert candidate("bIt") == 0
                assert candidate("I feel good today. I will be productive. will I?") == 2
                assert candidate("You and I are going for a walk") == 0
                assert candidate("I. I. I.") == 3
                assert candidate("Isn't it nice? I think so.") == 1
        """),
        entry_point="is_bored",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H5",
        _prompt=textwrap.dedent("""\
            def can_arrange(arr):
                \"\"\"Create a function which returns the largest index of an element which
                is not greater than or equal to the element immediately preceding it. If
                no such element exists then return -1. The given array will not contain
                duplicate values.

                Examples:
                can_arrange([1,2,4,3,5]) = 3
                can_arrange([1,2,3]) = -1
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([1,2,4,3,5]) == 3
                assert candidate([1,2,4,5]) == -1
                assert candidate([1,4,2,5,6,7,8,9,10]) == 2
                assert candidate([4,8,5,7,3]) == 4
                assert candidate([]) == -1
        """),
        entry_point="can_arrange",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H6",
        _prompt=textwrap.dedent("""\
            def largest_smallest_integers(lst):
                \"\"\"
                Create a function that returns a tuple (a, b), where 'a' is
                the largest of negative integers, and 'b' is the smallest
                of positive integers in a list.
                If there is no negative or positive integers, return them as None.

                Examples:
                largest_smallest_integers([2, 4, 1, 3, 5, 7]) == (None, 1)
                largest_smallest_integers([]) == (None, None)
                largest_smallest_integers([0]) == (None, None)
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([2, 4, 1, 3, 5, 7]) == (None, 1)
                assert candidate([]) == (None, None)
                assert candidate([0]) == (None, None)
                assert candidate([-1, -2, 4, 5, 6]) == (-1, 4)
                assert candidate([1, 2, 3, 4, 5, 2, 3, 3, -3, -4, 0, 0, 0]) == (-3, 1)
        """),
        entry_point="largest_smallest_integers",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H7",
        _prompt=textwrap.dedent("""\
            def count_nums(arr):
                \"\"\"
                Write a function count_nums which takes an array of integers and returns
                the number of elements which has a sum of digits > 0.
                If a number is negative, then its first signed digit will be negative:
                e.g. -123 has signed digits -1, 2, 3.

                >>> count_nums([]) == 0
                >>> count_nums([-1, 11, -11]) == 1
                >>> count_nums([1, 1, 2]) == 3
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([]) == 0
                assert candidate([-1, -2, 0]) == 0
                assert candidate([1, 1, 2, -2, 3, 4, 5]) == 6
                assert candidate([1, 6, 9, -6, 0, 1, 5]) == 5
                assert candidate([1, 100, 98, -7, 1, -1]) == 4
                assert candidate([12, 23, 34, -45, -56, 0]) == 5
                assert candidate([-1, -1, 2, 0, 1]) == 2  # -1 has digit sum -1 ≤ 0
        """),
        entry_point="count_nums",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H8",
        _prompt=textwrap.dedent("""\
            def move_one_ball(arr):
                \"\"\"We have an array 'arr' of N integers arr[1], arr[2], ..., arr[N].The
                numbers in the array will be randomly ordered. Your task is to determine if
                it is possible to get an array sorted in non-decreasing order by performing
                the following operation on the given array:
                        You are allowed to perform right shift operation any number of times.

                One right shift operation means shifting all elements of the array by one
                position in the right direction. The last element of the array will be moved
                to the starting position in the array i.e. 0th index.

                If it is possible to obtain the sorted array by performing the above operation
                then return True else return False.
                If the given array is empty then return True.

                Note: The given list is guaranteed to have unique elements.

                For Example:

                move_one_ball([3, 4, 5, 1, 2])==>True
                Explanation: By performin 2 right shift operations, non-decreasing order can
                             be achieved for the given array.
                move_one_ball([3, 5, 4, 1, 2])==>False
                Explanation:It is not possible to get non-decreasing order for the given
                            array by performing any number of right shift operations.
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([3, 4, 5, 1, 2]) == True
                assert candidate([3, 5, 4, 1, 2]) == False
                assert candidate([]) == True
                assert candidate([1, 2, 3, 4, 5]) == True
                assert candidate([5, 4, 3, 2, 1]) == False
        """),
        entry_point="move_one_ball",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H9",
        _prompt=textwrap.dedent("""\
            def exchange(lst1, lst2):
                \"\"\"In this problem, you will implement a function that takes two lists of numbers,
                and determines whether it is possible to perform an exchange of elements
                between them to make lst1 a list of only even numbers.
                There is no limit on the number of exchanged elements between lst1 and lst2.
                If it is possible to exchange elements between the lst1 and lst2 to make
                all the elements of lst1 to be even, return "YES".
                Otherwise, return "NO".
                For example:
                exchange([1, 2, 3, 4], [1, 2, 3, 4]) => "YES"
                exchange([1, 2, 3, 4], [1, 5, 3, 4]) => "NO"
                It is assumed that the input lists will be non-empty.
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([1, 2, 3, 4], [1, 2, 3, 4]) == "YES"
                assert candidate([1, 2, 3, 4], [1, 5, 3, 4]) == "NO"
                assert candidate([1, 2, 3, 4], [2, 1, 4, 3]) == "YES"
                assert candidate([5, 7, 3], [2, 6, 4]) == "YES"
                assert candidate([5, 7, 3], [1, 6, 4]) == "NO"
                assert candidate([3, 2, 6, 1, 8, 9], [3, 5, 5, 1, 1, 1]) == "NO"
        """),
        entry_point="exchange",
        difficulty=Difficulty.HARD,
    ),
    HumanEvalTask(
        task_id="HE/H10",
        _prompt=textwrap.dedent("""\
            def numerical_letter_grade(grades):
                \"\"\"It is the last week of the semester and the teacher has to give the grades
                to students. The teacher has been making her own algorithm for grading.
                The only problem is, she has lost the code she used for grading.
                She has given you a list of GPAs for some students and you have to write
                a function that can output a list of letter grades using the following table:
                         GPA       |    Letter grade
                          4.0                A+
                        > 3.7                A
                        > 3.3                A-
                        > 3.0                B+
                        > 2.7                B
                        > 2.3                B-
                        > 2.0                C+
                        > 1.7                C
                        > 1.3                C-
                        > 1.0                D+
                        > 0.7                D
                        > 0.0                D-
                          0.0                E
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([4.0, 3, 1.7, 2, 3.5]) == ['A+', 'B+', 'C-', 'C+', 'A-']
                assert candidate([1.2]) == ['D+']
                assert candidate([0.5]) == ['D-']
                assert candidate([0.0]) == ['E']
                assert candidate([1.0, 0.3, 1.5, 2.8, 3.3]) == ['D+', 'D-', 'C-', 'B', 'B+']
                assert candidate([0.0, 0.7]) == ['E', 'D-']
        """),
        entry_point="numerical_letter_grade",
        difficulty=Difficulty.HARD,
    ),
]

# ---------------------------------------------------------------------------
# Starter set — 10 HumanEval problems for the Phase 1 milestone run
# ---------------------------------------------------------------------------

HUMANEVAL_10: list[HumanEvalTask] = [
    HumanEvalTask(
        task_id="HE/1",
        _prompt=textwrap.dedent("""\
            def separate_paren_groups(paren_string: str) -> list[str]:
                \"\"\"Input to this function is a string containing multiple groups of nested
                parentheses. Your goal is to separate those groups into separate strings and
                return the list of those. Separate groups are balanced (each open brace is
                properly closed) and not nested within each other. Ignore any spaces.

                >>> separate_paren_groups('( ) (( )) (( )( ))')
                ['()', '(())', '(()())']
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate('(()()) ((())) () ((())()())') == [
                    '(()())', '((()))', '()', '((())()())']
                assert candidate('() (()) ((())) (((())))') == [
                    '()', '(())', '((()))', '(((())))']
                assert candidate('(()(())((())))') == ['(()(())((())))']
                assert candidate('( ) (( )) (( )( ))') == ['()', '(())', '(()())']
        """),
        entry_point="separate_paren_groups",
        difficulty=Difficulty.MEDIUM,
    ),
    HumanEvalTask(
        task_id="HE/2",
        _prompt=textwrap.dedent("""\
            def truncate_number(number: float) -> float:
                \"\"\"Given a positive floating point number, it can be decomposed into
                an integer part (largest integer smaller than given number) and decimals
                (leftover part always smaller than 1). Return the decimal part of the number.

                >>> truncate_number(3.5)
                0.5
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate(3.5) == 0.5
                assert abs(candidate(1.33) - 0.33) < 1e-6
                assert abs(candidate(123.456) - 0.456) < 1e-6
        """),
        entry_point="truncate_number",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/3",
        _prompt=textwrap.dedent("""\
            from typing import List

            def below_zero(operations: List[int]) -> bool:
                \"\"\"You're given a list of deposit and withdrawal operations on a bank account
                that starts with zero balance. Your task is to detect if at any point the
                balance of the account falls below zero, and at that point function should
                return True. Otherwise it should return False.

                >>> below_zero([1, 2, 3])
                False
                >>> below_zero([1, 2, -4, 5])
                True
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([]) == False
                assert candidate([1, 2, -3, 1, 2, -3]) == False
                assert candidate([1, 2, -4, 5, 6]) == True
                assert candidate([1, -1, 2, -2, 5, -5, 4, -4]) == False
                assert candidate([1, -1, 2, -2, 5, -5, 4, -5]) == True
                assert candidate([1, -2, 2, -2, 5, -5, 4, -4]) == True
        """),
        entry_point="below_zero",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/4",
        _prompt=textwrap.dedent("""\
            from typing import List

            def mean_absolute_deviation(numbers: List[float]) -> float:
                \"\"\"For a given list of input numbers, calculate Mean Absolute Deviation
                around the mean of this dataset.
                Mean Absolute Deviation is the average absolute difference between each
                element and a centerpoint (mean in this case):
                MAD = average | x - x_mean |

                >>> mean_absolute_deviation([1.0, 2.0, 3.0, 4.0])
                1.0
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert abs(candidate([1.0, 2.0, 3.0]) - 2/3) < 1e-6
                assert abs(candidate([1.0, 2.0, 3.0, 4.0]) - 1.0) < 1e-6
                assert abs(candidate([1.0, 2.0, 3.0, 4.0, 5.0]) - 6/5) < 1e-6
        """),
        entry_point="mean_absolute_deviation",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/5",
        _prompt=textwrap.dedent("""\
            from typing import List

            def intersperse(numbers: List[int], delimeter: int) -> List[int]:
                \"\"\"Insert a number 'delimeter' between every two consecutive elements
                of input list `numbers'.

                >>> intersperse([], 4)
                []
                >>> intersperse([1, 2, 3], 4)
                [1, 4, 2, 4, 3]
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([], 7) == []
                assert candidate([5, 6, 3, 2], 8) == [5, 8, 6, 8, 3, 8, 2]
                assert candidate([2, 2, 2], 2) == [2, 2, 2, 2, 2]
        """),
        entry_point="intersperse",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/6",
        _prompt=textwrap.dedent("""\
            from typing import List

            def parse_nested_parens(paren_string: str) -> List[int]:
                \"\"\"Input to this function is a string represented multiple groups for
                nested parentheses separated by spaces. For each of the group, output the
                deepest level of nesting of parentheses.

                >>> parse_nested_parens('(()()) ((())) () ((())()())')
                [2, 3, 1, 3]
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate('(()()) ((())) () ((())()())') == [2, 3, 1, 3]
                assert candidate('() (()) ((())) (((())))') == [1, 2, 3, 4]
                assert candidate('(()(())((())))') == [4]
        """),
        entry_point="parse_nested_parens",
        difficulty=Difficulty.MEDIUM,
    ),
    HumanEvalTask(
        task_id="HE/7",
        _prompt=textwrap.dedent("""\
            from typing import List

            def filter_by_substring(strings: List[str], substring: str) -> List[str]:
                \"\"\"Filter an input list of strings only for ones that contain given
                substring.

                >>> filter_by_substring([], 'a')
                []
                >>> filter_by_substring(['abc', 'bacd', 'cde', 'array'], 'a')
                ['abc', 'bacd', 'array']
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([], 'john') == []
                assert candidate(['xxx', 'asd', 'xxy', 'john doe', 'xxxAAA', 'xxx'], 'xxx') == ['xxx', 'xxxAAA', 'xxx']
                assert candidate(['xxx', 'asd', 'aaaxxy', 'john doe', 'xxxAAA', 'xxx'], 'xx') == ['xxx', 'aaaxxy', 'xxxAAA', 'xxx']
                assert candidate(['grunt', 'trumpet', 'prune', 'gruesome'], 'run') == ['grunt', 'prune']
        """),
        entry_point="filter_by_substring",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/8",
        _prompt=textwrap.dedent("""\
            from typing import List, Tuple

            def sum_product(numbers: List[int]) -> Tuple[int, int]:
                \"\"\"For a given list of integers, return a tuple consisting of a sum and
                a product of all the integers in a list. Empty sum should be equal to 0
                and empty product should be equal to 1.

                >>> sum_product([])
                (0, 1)
                >>> sum_product([1, 2, 3, 4])
                (10, 24)
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([]) == (0, 1)
                assert candidate([1, 1, 1]) == (3, 1)
                assert candidate([100, 0]) == (100, 0)
                assert candidate([3, 5, 7]) == (15, 105)
                assert candidate([10]) == (10, 10)
        """),
        entry_point="sum_product",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/9",
        _prompt=textwrap.dedent("""\
            from typing import List, Tuple

            def rolling_max(numbers: List[int]) -> List[int]:
                \"\"\"From a given list of integers, generate a list of rolling maximum
                element found until given moment in the sequence.

                >>> rolling_max([1, 2, 3, 2, 3, 4, 2])
                [1, 2, 3, 3, 3, 4, 4]
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate([]) == []
                assert candidate([1, 2, 3, 4]) == [1, 2, 3, 4]
                assert candidate([4, 3, 2, 1]) == [4, 4, 4, 4]
                assert candidate([3, 2, 3, 100, 3]) == [3, 3, 3, 100, 100]
        """),
        entry_point="rolling_max",
        difficulty=Difficulty.EASY,
    ),
    HumanEvalTask(
        task_id="HE/10",
        _prompt=textwrap.dedent("""\
            def is_palindrome(string: str) -> bool:
                \"\"\"Test if given string is a palindrome.\"\"\"
                return string == string[::-1]

            def make_palindrome(string: str) -> str:
                \"\"\"Find the shortest palindrome that begins with a supplied string.
                Algorithm idea is simple:
                - Find the longest postfix of supplied string that is a palindrome.
                - Append to the end of the string reverse of a string prefix that
                  comes before the palindromic suffix.

                >>> make_palindrome('')
                ''
                >>> make_palindrome('cat')
                'catac'
                >>> make_palindrome('cata')
                'catac'
                \"\"\"
        """),
        test_code=textwrap.dedent("""\
            def check(candidate):
                assert candidate('') == ''
                assert candidate('x') == 'x'
                assert candidate('xyz') == 'xyzyx'
                assert candidate('xyx') == 'xyx'
                assert candidate('jerry') == 'jerryrrej'
        """),
        entry_point="make_palindrome",
        difficulty=Difficulty.MEDIUM,
    ),
]
