from BeautifulSoup import BeautifulSoup
import re
import sys

# Yes it's crazy that these are inline styles rather than classes.
DISTRIBUTION_REQUIREMENTS_STYLE_STRING = 'color:#990000'

# class name is the next sibling after the bb class
# <tr valign="top" style="background-color:#F0F0F0">
#       <td class="bb">
#         <nobr>SOC&nbsp;
# 010</nobr>
#       </td>
#       <td>
#         <b>
#           <i>Racism</i>
#         </b>
#         <br>(same as: 
#             <span class="s">AFR S&nbsp;
# <nobr>010</nobr></span>)
#       </td>
#       <td class="s" align="right">
#         <nobr>Social and Behavioral Sciences</nobr>
#         <wbr>
#         <br>
#       </td>
#     </tr>

def ExtractCourseTitle(node):
  """Return the title of the course as a string"""
  # Title appears in between italics
  return node.find('i').text.strip()

def ExtractAliases(node):
  """Return a list of (Department, Number) tuples, or empty list if no aliases found"""
  #(same as: 
  #              <span class="s">SOC&nbsp;
  #  <nobr>010</nobr></span>)
  alias_nodes = node.findAll('span', {'class':'s'})
  # Department&nbsp;<nobr>course_number</nobr>
  aliases = []
  for alias_node in alias_nodes:
    department = alias_node.text.split('&nbsp;')[0].strip()
    course_number = alias_node.find('nobr').text.strip()
    aliases.append((department, course_number))
  return aliases

def ExtractDepartmentAndNumber(node):
  department, number = node.text.replace('&nbsp;', ' ').split('\n')
  department = department.strip()
  number = number.strip()
  return department, number

def ExtractDivision(node):
  """Returns top level division, e.g. Social and Behavioral Sciences, or empty string"""
  nodes = node.findAll('nobr')
  if nodes:
    return nodes[0].text.strip()
  else:
    return ''
  
def ExtractDistributionRequirements(node):
  """Returns the list of distribution requirements this course meets, e.g. Exploring Social Differences"""
  dist_requirements_nodes = node.findAll('nobr', {'style':DISTRIBUTION_REQUIREMENTS_STYLE_STRING})
  return [dist_node.text.strip() for dist_node in dist_requirements_nodes]

def ExtractDescription(node):
  nodes = node.findAll('div', {'class':'desc'})
  if nodes:
    return nodes[0].text.strip()
  else:
    return ''
    
    
def ExtractLocationAndTimes(tr):
  # <tr>
  #   <td class="s">&nbsp;
  #     </td>
  #   <td valign="top" align="left" class="s">
  #   <nobr>Adams-114</nobr>
  #   <br />
  #   <nobr>T&nbsp;
  #     2:30&nbsp;
  #     3:55<br />TH&nbsp;
  #     2:30&nbsp;
  #     3:55<br /></nobr>
  #   </td>
  #   <td align="right" class="s">
  #                     Current Enrollment: 12
  #                       of 16</td>
  #   </tr>
  #   
  # First nobr elem within first td contains the location
  
  """Returns 2 tuple (location, [list of times])"""
  class_node = tr.find('td', {'align':'left', 'class': 's'})
  unknown = ('', [])
  if not class_node:
    return unknown
  no_br_nodes = class_node.findAll('nobr')
  if len(no_br_nodes) == 2:
    loc = no_br_nodes[0].text
    time_string = no_br_nodes[1].text
    # TODO(ndunn): Fix this
    return loc, [time_string]
  return unknown
    
  
def ExtractEnrollment(tr):
  return ''
  
def ExtractFinalExamInfo(tr):
  return ''

def ExtractComments(tr):
  return ''
  
# TODO(ndunn): How to handle 'any AFR S 100-199'?  Or conjunctions vs disjunctions?
def ExtractRules(tr):
  """Given a node, determines all the rules which govern the course.
  
  Returns:
    a dictionary of requirements
  """
  if not tr:
    return {}
  
  # TODO(ndunn): Calculate prereqs
  rules_div = tr.find('div', {'style':'display:none;'})
  if not rules_div:
    return {}
  
  # Restriction or Inclusion
  
  # Priority Order
  
  # Prereqs - 'Must have taken'
  # Look for unordered list
  necessary_class_ul = rules_div.findAll('ul')
  necessary_classes = []
  if necessary_class_ul:
    necessary_classes_nodes = [node.find('nobr') for node in necessary_class_ul]
    for node in necessary_classes_nodes:
      if '&nbsp;' in node.text:
        # &nbsp; separates the department from the number 
        department, number = [x.strip() for x in node.text.split('&nbsp;')]
        necessary_classes.append((department, number))
      else:
        necessary_classes.append(node.text)
      
  return {'prereqs':necessary_classes}

def ExtractCourseInfo(tr):
  """Given tr containing course info, returns a Course object"""
  tds = tr.findAll('td')
  assert len(tds) == 3
  
  # td 0 has the department and number
  department, number = ExtractDepartmentAndNumber(tds[0])
  
  # td 1 has the title and optionally the aliases
  title = ExtractCourseTitle(tds[1])
  aliases = ExtractAliases(tds[1])
  
  description_tr = tr.findNextSibling('tr')
  # This tr contains most data; the next tr in table contains description
  description = ExtractDescription(description_tr)
  # The tr after the description contains location and enrollment
  location_tr = description_tr.findNextSibling('tr')
  location, times = ExtractLocationAndTimes(location_tr)
  enrollment = ExtractEnrollment(location_tr)
  
  # The tr after location + enrollment contains instructor, instructor email,
  # class email, final exam info
  instructor_tr = location_tr.findNextSibling('tr')
  #instructor_info = ExtractInstructorInfo(instructor_tr)
  #class_email = ExtractClassEmail(instructor_tr)
  #final_exam_info = ExtractFinalExamInfo(instructor_tr)
  
  # OPTIONAL comments section
  
  # tr after instructor info contains comments
  comments_tr = instructor_tr.findNextSibling('tr')
  if 'Comments' in comments_tr.text:
    comments = ExtractComments(comments_tr)
  else:
    comments = ''
  
  # final tr contains rules + prereqs
  rules_tr = [tr for tr in tr.findNextSiblings('tr') if 'Rules' in tr.text][0]
  rules = ExtractRules(rules_tr)
  
  # td 2 has the type of the course - e.g. Social and Behavioral Sciences
  division = ExtractDivision(tds[2])
  distribution_requirements_fulfilled = ExtractDistributionRequirements(tds[2])
  
  return Course(department=department, 
                course_number=number,  
                title=title,
                description=description,
                division=division,
                location=location,
                distribution_requirements_fulfilled=distribution_requirements_fulfilled,
                alias_list=aliases,
                prereqs=rules.get('prereqs', []),
                times=times
                )
  
class Course(object):
  def __init__(self, 
              department, 
              course_number,
              title,
              description,
              division,
              location,
              distribution_requirements_fulfilled=None,
              alias_list=None,
              prereqs=None,
              comments=None,
              times=None):
    self.department = department
    self.course_number = course_number
    self.title = title
    self.description = description
    self.location = location
    self.distribution_requirements_fulfilled = distribution_requirements_fulfilled or []
    self.alias_list = alias_list or []
    self.prereqs = prereqs or []
    self.comments = comments or []
    self.times = times or []
    
  def __str__(self):
    return "%s %s %s" %(self.department, self.course_number, self.title)
    
def MakeId(department, course_number):    
  return department.replace(' ', '_') + '_' + course_number
    
def GetCourseId(course):
  return MakeId(course.department, course.course_number)

def GetCourseLabel(course):
  return ' '.join([course.department, course.course_number])
    
def GetDependencyGraph(courses):
  graph = """
digraph Bowdoin2012Spring {
  graph [rankdir="BT"]
  node [shape=plaintext]
  
  """
  # Print the course nodes and labels
  for course in courses:
    graph += GetCourseId(course) + '[label="%s"]\n' %GetCourseLabel(course)
    
  # Print the dependencies
  for course in courses:
    for prereq in course.prereqs:
      if len(prereq) == 2:
        department = prereq[0]
        course_number = prereq[1]
        graph += '%s -> %s\n' %(GetCourseId(course), MakeId(department, course_number))
      else:
        print >> sys.stderr, "Couldn't parse '%s'" %(prereq)
      
  graph += '}'
  return graph
    
def main():
  soup = BeautifulSoup(open('CourseCatalog.html'))

  # The class names are held in td elems with class "bb".  The underlying table row has
  # even more metadata
  bbs = soup.findAll('td', {'class':'bb'})
  # trs containining class info:
  trs = map(lambda bb:bb.parent, bbs)
  
  courses = map(ExtractCourseInfo, trs)
  
  # Print the DOT map
  
  
  print courses
      
    
if __name__ == '__main__':
  main()
#all_classes = map(ExtractDepartmentAndNumber, bbs)
#>>> print len(all_classes)
#567
  