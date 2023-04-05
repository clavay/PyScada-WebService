PyScada WebService Extension
============================

This is a extension for PyScada to support read and write to Web Services.


What is Working
---------------

 - nothing is test


What is not Working/Missing
---------------------------

 - Test with real hardware
 - Documentation

Installation
------------

 - pip install https://github.com/pyscada/PyScada-WebService/tarball/master


How to
------

 - Put the IP or DNS in the device option
 - To read :
    - Put in the action path
    - Put in the variable path :
    - For XML look at https://docs.python.org/3/library/xml.etree.elementtree.html#xpath-support
        - .//\*[.="mode"]../Value
        - .//\*[@name='Singapore']/year
        - ...
    - For JSON write nested dict as a space separated string : dict1 dict2 ...
 - To write :
    - You have to move the variables in chosen variables
    - Put in the action path $x to refer to variable with id x
    - /example1/$5/$2/blablabla/$8
    - Select the trigger variable (write all the variable when the trigger is true)


Contribute
----------

 - Issue Tracker: https://github.com/pyscada/PyScada-WebService/issues
 - Source Code: https://github.com/pyscada/PyScada-WebService
 

License
-------

The project is licensed under the _GNU AFFERO GENERAL PUBLIC LICENSE Version 3 (AGPLv3)_.
-
