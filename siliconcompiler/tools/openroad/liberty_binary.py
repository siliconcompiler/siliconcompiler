import gzip
import os
import shutil

from typing import Optional, Union

from siliconcompiler.tools.openroad import OpenROADTask


class LibertyBinaryTask(OpenROADTask):
    '''
    Convert the liberty files of :keypath:`ASIC,asic,mainlib` to binary liberty
    (``.blib``), which OpenROAD loads faster than the text format. The files
    converted are those in the library's corner filesets for
    :keypath:`ASIC,asic,delaymodel`.

    Each output is named after its source, so ``<name>.lib.gz`` becomes
    ``<name>.blib.gz``. Added to the fileset its source came from, a binary
    liberty file is read by OpenROAD in place of the text files in that fileset;
    other tools keep reading the text liberty.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("compress", "bool",
                           "true/false, when true the binary liberty files are written "
                           "gzip compressed", defvalue=True)
        # str rather than dir: the directory need not exist until it is installed to
        self.add_parameter("installpath", "str",
                           "absolute path of a directory to also copy the binary liberty "
                           "files into")

    def set_openroad_compress(self, enable: bool,
                              step: Optional[str] = None,
                              index: Optional[Union[int, str]] = None):
        """
        Enables or disables gzip compression of the binary liberty files.

        Args:
            enable (bool): True to write ``.blib.gz`` files, False to write ``.blib``.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "compress", enable, step=step, index=index)

    def set_openroad_installpath(self, path: str,
                                 step: Optional[str] = None,
                                 index: Optional[Union[int, str]] = None):
        """
        Sets a directory to also copy the binary liberty files into.

        Args:
            path (str): Absolute path of the directory, created if missing.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "installpath", path, step=step, index=index)

    def task(self):
        return "liberty_binary"

    def setup(self):
        self.set_threads(1)

        super().setup()

        self.set_script("sc_liberty_binary.tcl")

        # write_liberty_binary arrived with 26Q4-509
        self.add_version(">=26Q4-509", clobber=True)

        self.add_required_key("asic", "mainlib")
        self.add_required_key("asic", "delaymodel")
        self.add_required_key("var", "compress")
        ext = "blib.gz" if self.get("var", "compress") else "blib"

        installpath = self.get("var", "installpath")
        if installpath:
            # A relative path would resolve inside the node's working directory
            if not os.path.isabs(installpath):
                raise ValueError(f"installpath must be an absolute path: {installpath}")
            self.add_required_key("var", "installpath")

        # sc_liberty_binary.tcl derives the same output names
        delaymodel = self._get_delaymodel()
        lib = self.mainlib
        sources = {}
        for corner in lib.getkeys("asic", "libcornerfileset"):
            if not lib.valid("asic", "libcornerfileset", corner, delaymodel):
                continue
            self.add_required_key(lib, "asic", "libcornerfileset", corner, delaymodel)
            for fileset in lib.get("asic", "libcornerfileset", corner, delaymodel):
                if not lib.has_file(fileset=fileset, filetype="liberty"):
                    continue
                self.add_required_key(lib, "fileset", fileset, "file", "liberty")
                for source in lib.get("fileset", fileset, "file", "liberty"):
                    name = os.path.basename(source)
                    if name.lower().endswith(".gz"):
                        name = name[:-3]
                    output = f"{os.path.splitext(name)[0]}.{ext}"
                    if sources.setdefault(output, source) != source:
                        raise ValueError(f"{source} and {sources[output]} would both be "
                                         f"converted to {output}")

        if not sources:
            raise ValueError(f"{lib.name} has no {delaymodel} liberty files to convert")

        for output in sorted(sources):
            self.add_output_file(output)

    def post_process(self):
        super().post_process()

        installpath = self.get("var", "installpath")
        if installpath:
            installpath = os.path.abspath(installpath)
            self.logger.info(f"Installing into {installpath}")
            os.makedirs(installpath, exist_ok=True)

        for output in self.get("output"):
            path = os.path.join("outputs", output)
            if self.get("var", "compress"):
                # write_liberty_binary cannot write gzip itself, read_liberty reads
                # it; mtime=0 keeps the output identical across runs
                blib = path[:-len(".gz")]
                with open(blib, "rb") as fin, open(path, "wb") as fout, \
                        gzip.GzipFile(fileobj=fout, mode="wb", mtime=0) as gzout:
                    shutil.copyfileobj(fin, gzout)
                os.remove(blib)

            if installpath:
                shutil.copy(path, installpath)
