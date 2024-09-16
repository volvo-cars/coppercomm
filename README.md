Coppercomm
==========

Coppercomm is a lightweight library, written in Python. It is used by tests for communicating through different protocols.

![Coppercomm overview](https://raw.githubusercontent.com/volvo-cars/coppercomm/cf0f53986e5d438f1c485191af390252ece99e19/images/coppercomm_overview.png)

Introduction
------------
In big organizations it is not uncommon that some of the code is delivered by a vendor, that has their own set of test cases. The vendor test cases can be run before delivery of the code. These test cases can be very useful to be executed by the receiving end, after the code from the vendor has been intergrated into a system. Executing the same test case "before" and "after" makes it easier to troubleshoot, especially if it is the exact same test case.
One challenge with sharing test cases across different organizations/companies is the use of different libraries, for solving the same problem. This causes the reuse of test cases to be complicated. When Coppercomm is used, the names of the interfaces are the same, and a configuration file under the hood keeps track of what physical or logical unit the interface represents.

When test cases across companies and organizations are using Coppercomm, the test cases can be executed without modifications or if-statements for different environments, in the test cases. It becomes convenient to execute test cases at different places.

![Coppercomm overview](https://raw.githubusercontent.com/volvo-cars/coppercomm/cf0f53986e5d438f1c485191af390252ece99e19/images/coppercomm_config.png)

Examples
--------
There are some examples on how to use it here:
[test_example_pytest.py](https://raw.githubusercontent.com/volvo-cars/coppercomm/cf0f53986e5d438f1c485191af390252ece99e19/examples/test_example_pytest.py).

