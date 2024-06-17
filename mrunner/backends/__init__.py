# pylint: disable=import-outside-toplevel,missing-function-docstring


def get_backend(backend_type):
    if backend_type == "kubernetes":
        from mrunner.backends.k8s import get_kubernetes_backend

        return get_kubernetes_backend()
    if backend_type == "slurm":
        from mrunner.backends.slurm import get_slurm_backend

        return get_slurm_backend()

    raise KeyError(f"No backend type: {backend_type}")


def get_context_cls(backend_type):
    if backend_type == "kubernetes":
        from mrunner.backends.k8s import KubernetesContext

        return KubernetesContext
    if backend_type == "slurm":
        from mrunner.backends.slurm import SlurmContext

        return SlurmContext

    raise KeyError(f"No backend type: {backend_type}")
