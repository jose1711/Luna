import subprocess
import threading
import time
import re

import xbmc
import xbmcgui

class MoonlightHelper:

    config_helper = None
    pin_received = False
    pairing_messages = ""

    def __init__(self, plugin, config_helper, logger):
        self.plugin = plugin
        self.config_helper = config_helper
        self.logger = logger

    def loop_lines(self, logger, iterator, dialog):
        for line in iterator:
            xbmc.log(line.strip(), xbmc.LOGERROR)
            if line.strip() == "":
                break
            if 'enter the following PIN' in line:
                dialog.update(50, line)
                self.pin_received = True
            elif self.pin_received:
                self.pairing_messages += line.strip() + '\n'

    def pair(self):
        binary_path = self.config_helper.binary_path
        self.pair_success = False
        try:
            pairing_proc = subprocess.Popen([binary_path + "moonlight", "pair"], cwd=binary_path, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            lines_iterator = iter(pairing_proc.stdout.readline, "")
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                self.plugin.getLocalizedString(30000),
                'Starting Pairing'
            )

            pairing_thread = threading.Thread(target=self.loop_lines, args=(self.logger, lines_iterator, dialog))
            pairing_thread.start()

            pairing_proc.wait(timeout=30)
            dialog.close()
            if 'Succesfully paired' in self.pairing_messages:
                xbmcgui.Dialog().ok(self.plugin.getLocalizedString(30000), 'Pairing successful')
            else:
                raise Exception('Pairing failed or already paired!')
        except Exception as e:
            if len(self.pairing_messages) < 5:
                self.pairing_messages = "Pairing failed:\n" + str(e)
            xbmcgui.Dialog().ok(self.plugin.getLocalizedString(30000), self.pairing_messages)

    def list_games(self):
        binary_path = self.config_helper.binary_path
        list_regex = r'\d+\.\s+([^\n]*)'

        try:
            moonlightOut = subprocess.check_output(['moonlight', 'list'], cwd=binary_path, timeout=5, encoding='utf-8', start_new_session=True)

            if 'must pair' in moonlightOut:
                return True

            return re.findall(list_regex, moonlightOut)
        except:
            return False

    def quit_game(self):
        binary_path = self.config_helper.binary_path
        try:
            subprocess.run(['moonlight', 'quit'], cwd=binary_path, timeout=5, start_new_session=True)
        except:
            return False

        return True

    def launch_game(self, game_id):
        binary_path = self.config_helper.binary_path
        scripts_path = self.config_helper.launchscripts_path

        player = xbmc.Player()
        if player.isPlayingVideo():
            player.stop()

        isResumeMode = bool(self.plugin.getSetting('last_run'))
        showIntro = self.plugin.getSettingBool('show_intro')
        codec = self.config_helper.config['codec']

        if isResumeMode:
            xbmc.audioSuspend()
        else:
            self.plugin.setSettingString('last_run', game_id)

        xbmc.executebuiltin("Dialog.Close(busydialog)")
        xbmc.executebuiltin("Dialog.Close(notification)")
        xbmc.executebuiltin("InhibitScreensaver(true)")

        try:
            if showIntro and not isResumeMode:
                player.play(self.config_helper.addon_path + 'resources/statics/loading.mp4')
                time.sleep(9)
                player.stop()

            t0 = time.monotonic()
            subprocess.run([scripts_path + 'prescript.sh', binary_path, codec], cwd=scripts_path, start_new_session=True)
            launch_cmd = subprocess.Popen([scripts_path + 'launch.sh', game_id], cwd=binary_path, start_new_session=True)
            launch_cmd.wait()
            subprocess.run([scripts_path + 'postscript.sh', binary_path], cwd=scripts_path, start_new_session=True)

        except Exception as e:
            print("Failed to execute moonlight process.")
            print(e)
        finally:
            xbmc.audioResume()
            xbmc.executebuiltin("InhibitScreensaver(false)")

            # Less than 10 seconds passed.
            if time.monotonic() - t0 < 10:
                result = xbmcgui.Dialog().yesno("", "It seems that moonlight-embedded might have crashed. Create an automatic bug report?")
                if result:
                    output = subprocess.check_output([scripts_path + '../../create_bug_report.sh'], encoding='utf-8', cwd=scripts_path+'../../', start_new_session=True)
                    xbmcgui.Dialog().ok("", "Report your bug on GitHub or Forums with this URL: " + output)
            else:
                xbmcgui.Dialog().notification('Information', game_id + ' is still running on host. Resume via Luna, ensuring to quit before the host is restarted!', xbmcgui.NOTIFICATION_INFO, False)
