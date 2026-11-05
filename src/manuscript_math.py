"""Editable OMML for the six ordinary equations used in the methods."""
from docx.oxml import OxmlElement

def r(text):
    e=OxmlElement('m:r');t=OxmlElement('m:t');t.text=text;e.append(t);return e

def slot(name,nodes):
    e=OxmlElement(name)
    for n in nodes:e.append(n)
    return e

def sub(base,index):
    e=OxmlElement('m:sSub');e.append(slot('m:e',[r(base)]));e.append(slot('m:sub',[r(index)]));return e

def sup(base,power):
    e=OxmlElement('m:sSup');e.append(slot('m:e',[r(base)]));e.append(slot('m:sup',[r(power)]));return e

def frac(num,den):
    e=OxmlElement('m:f');e.append(slot('m:num',num));e.append(slot('m:den',den));return e

def equation(key,number=None):
    if key=='HQ':parts=[r('Q = H (1 − '),frac([sup('D','2.5')],[sup('D','2.5'),r(' + '),sup('k','2.5')]),r(')')]
    elif key=='standardize':parts=[sub('z','ij'),r(' = '),frac([sub('x','ij'),r(' − '),sub('x','j,min')],[sub('x','j,max'),r(' − '),sub('x','j,min')])]
    elif key=='proportion':parts=[sub('p','ij'),r(' = '),frac([sub('z','ij')],[sub('∑','i'),r(' '),sub('z','ij')])]
    elif key=='entropy':parts=[sub('e','j'),r(' = −'),frac([sub('∑','i'),r(' '),sub('p','ij'),r(' ln '),sub('p','ij')],[r('ln n')])]
    elif key=='weight':parts=[sub('w','j'),r(' = '),frac([r('1 − '),sub('e','j')],[sub('∑','j'),r(' (1 − '),sub('e','j'),r(')')])]
    elif key=='ER':parts=[sub('ER','i'),r(' = '),sub('∑','j'),r(' '),sub('w','j'),r(' '),sub('z','ij')]
    else:raise ValueError(key)
    if number is not None:parts.append(r('     （'+str(number)+'）'))
    return slot('m:oMath',parts)
