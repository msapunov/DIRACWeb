import logging
import os

from dirac.lib.base import *
from DIRAC import gConfig, gLogger
from dirac.lib.diset import getRPCClient
from dirac.lib.credentials import getUserDN, getUsername, getAvailableGroups, getProperties
from DIRAC.FrameworkSystem.Client.NotificationClient import NotificationClient
from DIRAC.Core.Utilities.List import uniqueElements

log = logging.getLogger( __name__ )

class GeneralController( BaseController ):

  def index( self ):
    return redirect_to( controller = "info/general", action = "diracOverview" )

  def diracOverview( self ):
    return render( "/info/diracOverview.mako" )

  def ext4test( self ):
    return render( "/info/ext4test.mako" )
        
  @jsonify
  def action(self):
    if request.params.has_key("getVOList") and len(request.params["getVOList"]) > 0:
      return {"success":"true","result":self.getVOList()}
    elif request.params.has_key("getCountries") and len(request.params["getCountries"]) > 0:
      return {"success":"true","result":self.getCountries()}
    elif request.params.has_key("registration_request") and len(request.params["registration_request"]) > 0:
      paramcopy = dict()
      for i in request.params:
        if not i == "registration_request" and len(request.params[i]) > 0:
          paramcopy[i] = request.params[i]
      return self.registerUser(paramcopy)
    else:
      return {"success":"false","error":"The request parameters can not be recognized or they are not defined"}

  def registerUser(self,paramcopy):
# Unfortunately there is no way to get rid of empty text values in JS, so i have to hardcode it on server side. Hate it!
    default_values = ["John Smith","jsmith","john.smith@gmail.com","+33 9 10 00 10 00","Select prefered virtual organization(s)"]
    default_values.append("Select your country")
    default_values.append("Any additional information you want to provide to administrators")
    dn = getUserDN()
    username = getUsername()
    if not username == "anonymous":
      return {"success":"false","error":"You are already registered in DIRAC with username: %s" % username}
    else:
      if not dn:
        return {"success":"false","error":"You have to load certificate to your browser before trying to register"}
    body = ""
    userMail = False
    vo = []
    for i in paramcopy:
      if not paramcopy[i] in default_values:
        if i == "email":
          userMail = paramcopy[i]
        if i == "vo":
          vo = paramcopy[i].split(",")
        body = body + str(i) + ' - "' + str(paramcopy[i]) + '"\n'
    if not userMail:
      return {"success":"false","error":"Can not get your email from the request"}
    gLogger.info("!!! VO: ",vo)
# TODO Check for previous requests
    if not len(vo) > 0:
      mails = gConfig.getValue("/Website/UserRegistrationEmail",[])
    else:
      mails = []
      for i in vo:
        i = i.strip()
        voadm = gConfig.getValue("/Registry/VO/%s/VOAdmin" % i,"")
        failsafe = False
        if voadm:
          tmpmail = gConfig.getValue("/Registry/Users/%s/Email" % voadm,"")
          if tmpmail:
            mails.append(tmpmail)
          else:
            gLogger.error("Can not find value for option /Registry/Users/%s/Email Trying failsafe option" % voadm)
            failsafe = True
        else:
          gLogger.error("Can not find value for option /Registry/VO/%s/VOAdmin Trying failsafe option" % i)
          failsafe = True
        if failsafe:
          failsafe = gConfig.getValue("/Website/UserRegistrationEmail",[])
          if len(failsafe) > 0:
            for j in failsafe:
              mails.append(j)
          else:
              gLogger.error("Can not find value for failsafe option /Website/UserRegistrationEmail User registration for VO %s is failed" % i)
    mails = uniqueElements(mails)
    if not len(mails) > 0:
      groupList = list()
      allGroups = gConfig.getSections("/Registry/Groups")
      if not allGroups["OK"]:
        return {"success":"false","error":"No groups found at this DIRAC installation"}
      allGroups = allGroups["Value"]
      for j in allGroups:
        props = getProperties(j)
        if "UserAdministrator" in props: # property which usd for user administration
          groupList.append(j)
      groupList = uniqueElements(groupList)
      if not len(groupList) > 0:
        return {"success":"false","error":"No groups, resposible for user administration, found"}
      userList = list()
      for i in groupList:
        users = gConfig.getValue("/Registry/Groups/%s/Users" % i,[])
        for j in users:
          userList.append(j)
      userList = uniqueElements(userList)
      if not len(userList) > 0:
        return {"success":"false","error":"Can not find a person resposible for user administration, your request can not be approuved"}
      mails = list()
      mail2name = dict()
      for i in userList:
        tmpmail = gConfig.getValue("/Registry/Users/%s/Email" % i,"")
        if tmpmail:
          mails.append(tmpmail)
        else:
          gLogger.error("Can not find value for option /Registry/Users/%s/Email" % i)
      mails = uniqueElements(mails)
      if not len(mails) > 0:
        return {"success":"false","error":"Can not find an email of the person resposible for the users administration, your request can not be approuved"}
    gLogger.info("Admins emails: ",mails)
    if not len(mails) > 0:
      return {"success":"false","error":"Can not find any emails of DIRAC Administrators"}
    allUsers = gConfig.getSections("/Registry/Users")
    if not allUsers["OK"]:
      return {"success":"false","error":"No users found at this DIRAC installation"}
    allUsers = allUsers["Value"]
    mail2name = dict()
    for i in allUsers:
      tmpmail = gConfig.getValue("/Registry/Users/%s/Email" % i,"")
      if tmpmail in mails:
        mail2name[tmpmail] = gConfig.getValue("/Registry/Users/%s/FullName" % i,i)
    sentFailed = list()
    sentSuccess = list()
    errorMessage = list()
    ntc = NotificationClient( getRPCClient )
    for i in mails:
      i = i.strip()
      result = ntc.sendMail(i,"New user has registered",body,userMail,False)
      if not result["OK"]:
        sentFailed.append(mail2name[i])
        errorMessage.append(result["Message"])
      else:
        sentSuccess.append(mail2name[i])
    gLogger.info("Sent success: ",sentSuccess)
    gLogger.info("Sent failure: ",sentFailed)
    errorMessage = uniqueElements(errorMessage)
    if len(sentSuccess) == 0:
      if not len(errorMessage) > 0:
        return {"success":"false","error":"No messages were sent to administrators due techincal reasons"}
      errorMessage = ", ".join(errorMessage)
      return {"success":"false","error":errorMessage}
    sName = ", ".join(sentSuccess)
    fName = ", ".join(sentFailed)
    if len(sentFailed) > 0:
      return {"success":"true","result":"Your registration request were sent successfuly to %s. Failed to sent request to %s." % (sName, fName)}
    return {"success":"true","result":"Your registration request were sent successfuly to %s." % sName}

  def getVOList(self):
    result = gConfig.getSections("/Registry/VO")
    if result["OK"]:
      vo = result["Value"]
    else:
      vo = ""
    return vo
    
  def getCountries(self):
    countries = {
    "af": "Afghanistan",
    "al": "Albania",
    "dz": "Algeria",
    "as": "American Samoa",
    "ad": "Andorra",
    "ao": "Angola",
    "ai": "Anguilla",
    "aq": "Antarctica",
    "ag": "Antigua and Barbuda",
    "ar": "Argentina",
    "am": "Armenia",
    "aw": "Aruba",
    "au": "Australia",
    "at": "Austria",
    "az": "Azerbaijan",
    "bs": "Bahamas",
    "bh": "Bahrain",
    "bd": "Bangladesh",
    "bb": "Barbados",
    "by": "Belarus",
    "be": "Belgium",
    "bz": "Belize",
    "bj": "Benin",
    "bm": "Bermuda",
    "bt": "Bhutan",
    "bo": "Bolivia",
    "ba": "Bosnia and Herzegowina",
    "bw": "Botswana",
    "bv": "Bouvet Island",
    "br": "Brazil",
    "io": "British Indian Ocean Territory",
    "bn": "Brunei Darussalam",
    "bg": "Bulgaria",
    "bf": "Burkina Faso",
    "bi": "Burundi",
    "kh": "Cambodia",
    "cm": "Cameroon",
    "ca": "Canada",
    "cv": "Cape Verde",
    "ky": "Cayman Islands",
    "cf": "Central African Republic",
    "td": "Chad",
    "cl": "Chile",
    "cn": "China",
    "cx": "Christmas Island",
    "cc": "Cocos Islands",
    "co": "Colombia",
    "km": "Comoros",
    "cg": "Congo",
    "cd": "Congo",
    "ck": "Cook Islands",
    "cr": "Costa Rica",
    "ci": "Cote D'Ivoire",
    "hr": "Croatia",
    "cu": "Cuba",
    "cy": "Cyprus",
    "cz": "Czech Republic",
    "dk": "Denmark",
    "dj": "Djibouti",
    "dm": "Dominica",
    "do": "Dominican Republic",
    "tp": "East Timor",
    "ec": "Ecuador",
    "eg": "Egypt",
    "sv": "El Salvador",
    "gq": "Equatorial Guinea",
    "er": "Eritrea",
    "ee": "Estonia",
    "et": "Ethiopia",
    "fk": "Falkland Islands",
    "fo": "Faroe Islands",
    "fj": "Fiji",
    "fi": "Finland",
    "fr": "France",
    "fx": "France, metropolitan",
    "gf": "French Guiana",
    "pf": "French Polynesia",
    "tf": "French Southern Territories",
    "ga": "Gabon",
    "gm": "Gambia",
    "ge": "Georgia",
    "de": "Germany",
    "gh": "Ghana",
    "gi": "Gibraltar",
    "gr": "Greece",
    "gl": "Greenland",
    "gd": "Grenada",
    "gp": "Guadeloupe",
    "gu": "Guam",
    "gt": "Guatemala",
    "gn": "Guinea",
    "gw": "Guinea-Bissau",
    "gy": "Guyana",
    "ht": "Haiti",
    "hm": "Heard and Mc Donald Islands",
    "va": "Vatican City",
    "hn": "Honduras",
    "hk": "Hong Kong",
    "hu": "Hungary",
    "is": "Iceland",
    "in": "India",
    "id": "Indonesia",
    "ir": "Iran",
    "iq": "Iraq",
    "ie": "Ireland",
    "il": "Israel",
    "it": "Italy",
    "jm": "Jamaica",
    "jp": "Japan",
    "jo": "Jordan",
    "kz": "Kazakhstan",
    "ke": "Kenya",
    "ki": "Kiribati",
    "kp": "Korea",
    "kr": "Korea",
    "kw": "Kuwait",
    "kg": "Kyrgyzstan",
    "la": "Lao",
    "lv": "Latvia",
    "lb": "Lebanon",
    "ls": "Lesotho",
    "lr": "Liberia",
    "ly": "Libyan",
    "li": "Liechtenstein",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "mo": "Macau",
    "mk": "Macedonia",
    "mg": "Madagascar",
    "mw": "Malawi",
    "my": "Malaysia",
    "mv": "Maldives",
    "ml": "Mali",
    "mt": "Malta",
    "mh": "Marshall Islands",
    "mq": "Martinique",
    "mr": "Mauritania",
    "mu": "Mauritius",
    "yt": "Mayotte",
    "mx": "Mexico",
    "fm": "Micronesia",
    "md": "Moldova",
    "mc": "Monaco",
    "mn": "Mongolia",
    "ms": "Montserrat",
    "ma": "Morocco",
    "mz": "Mozambique",
    "mm": "Myanmar",
    "na": "Namibia",
    "nr": "Nauru",
    "np": "Nepal",
    "nl": "Netherlands",
    "an": "Netherlands Antilles",
    "nc": "New Caledonia",
    "nz": "New Zealand",
    "ni": "Nicaragua",
    "ne": "Niger",
    "ng": "Nigeria",
    "nu": "Niue",
    "nf": "Norfolk Island",
    "mp": "Northern Mariana Islands",
    "no": "Norway",
    "om": "Oman",
    "pk": "Pakistan",
    "pw": "Palau",
    "pa": "Panama",
    "pg": "Papua New Guinea",
    "py": "Paraguay",
    "pe": "Peru",
    "ph": "Philippines",
    "pn": "Pitcairn",
    "pl": "Poland",
    "pt": "Portugal",
    "pr": "Puerto Rico",
    "qa": "Qatar",
    "re": "Reunion",
    "ro": "Romania",
    "ru": "Russia",
    "rw": "Rwanda",
    "kn": "Saint Kitts and Nevis",
    "lc": "Saint Lucia",
    "vc": "Saint Vincent and the Grenadines",
    "ws": "Samoa",
    "sm": "San Marino",
    "st": "Sao Tome and Principe",
    "sa": "Saudi Arabia",
    "sn": "Senegal",
    "sc": "Seychelles",
    "sl": "Sierra Leone",
    "sg": "Singapore",
    "sk": "Slovakia",
    "si": "Slovenia",
    "sb": "Solomon Islands",
    "so": "Somalia",
    "za": "South Africa",
    "gs": "South Georgia and the South Sandwich Islands",
    "es": "Spain",
    "lk": "Sri Lanka",
    "sh": "St. Helena",
    "pm": "St. Pierre and Miquelon",
    "sd": "Sudan",
    "sr": "Suriname",
    "sj": "Svalbard and Jan Mayen Islands",
    "sz": "Swaziland",
    "se": "Sweden",
    "ch": "Switzerland",
    "sy": "Syrian Arab Republic",
    "tw": "Taiwan",
    "tj": "Tajikistan",
    "tz": "Tanzania",
    "th": "Thailand",
    "tg": "Togo",
    "tk": "Tokelau",
    "to": "Tonga",
    "tt": "Trinidad and Tobago",
    "tn": "Tunisia",
    "tr": "Turkey",
    "tm": "Turkmenistan",
    "tc": "Turks and Caicos Islands",
    "tv": "Tuvalu",
    "ug": "Uganda",
    "ua": "Ukraine",
    "ae": "United Arab Emirates",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "us": "United States",
    "um": "United States Minor Outlying Islands",
    "uy": "Uruguay",
    "uz": "Uzbekistan",
    "vu": "Vanuatu",
    "ve": "Venezuela",
    "vn": "Viet Nam",
    "vg": "Virgin Islands (British)",
    "vi": "Virgin Islands (U.S.)",
    "wf": "Wallis and Futuna Islands",
    "eh": "Western Sahara",
    "ye": "Yemen",
    "yu": "Yugoslavia",
    "zm": "Zambia",
    "zw": "Zimbabwe",
    "su": "Soviet Union"
    }
    return countries
